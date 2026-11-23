"""Run from the project root: python -m uvicorn backend.main:app --reload."""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from starlette.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import database
from .extraction import PDFError, extract_pdf
from .ratios import calculate_ratios
from .health import predict_health
from .sentiment import analyze_sentiment
from .demo import demo_analysis, fallback_analysis

MAX_BYTES = 20 * 1024 * 1024
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    database.initialize()
    app.state.processing = asyncio.Semaphore(1)
    yield


app = FastAPI(title="FinLens backend", version="0.1.0", lifespan=lifespan)
FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
app.mount("/assets", StaticFiles(directory=FRONTEND / "assets"), name="assets")


@app.get("/", include_in_schema=False)
def landing_page():
    return FileResponse(FRONTEND / "index.html")


@app.get("/upload", include_in_schema=False)
def upload_page():
    return FileResponse(FRONTEND / "upload.html")


@app.get("/results/{analysis_id}", include_in_schema=False)
def results_page(analysis_id: str):
    return FileResponse(FRONTEND / "results.html")


@app.get("/history", include_in_schema=False)
def history_page():
    return FileResponse(FRONTEND / "history.html")


@app.get("/api/demo")
def get_demo():
    return demo_analysis()


def analyze(data, filename):
    try:
        result = extract_pdf(data)
    except PDFError as exc:
        if 'No selectable text' not in str(exc):
            raise
        result = fallback_analysis(reason=str(exc))
    except Exception:
        log.exception('Extraction unavailable; returning labelled demonstration')
        result = fallback_analysis(reason='The extractor could not process this PDF layout.')
    if not result.get('is_fallback'):
        if (not any(value is not None for pair in result['metrics'].values() for value in pair.values())
                and not result.get('coverage', {}).get('reported_highlights')):
            result = fallback_analysis(result, 'No supported financial amounts were extracted from this report.')
        else:
            result["ratios"] = calculate_ratios(result["metrics"], result["balance"])
            try:
                result["health"] = predict_health(result["ratios"])
            except Exception:
                log.exception('Health model unavailable')
                from .health import rule_rating, feature_values
                result['health'] = rule_rating(feature_values(result['ratios']))
            try:
                result["sentiment"] = analyze_sentiment(result["commentary"])
            except Exception:
                log.exception('Sentiment unavailable')
                result['sentiment'] = {'status':'unavailable', 'reason':'Sentiment analysis is unavailable; extracted financial results are still shown.'}
    result.update(id=str(uuid4()), filename=filename + (' · Illustrative fallback' if result.get('is_fallback') else ''),
                  created_at=datetime.now(timezone.utc).isoformat())
    database.save(result)
    return result


@app.post("/api/analyze", status_code=201)
async def upload(file: UploadFile = File(...)):
    try:
        filename = (file.filename or "report.pdf").replace("\\", "/").split("/")[-1]
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(415, "Please upload a PDF file.")
        data = await file.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "PDF must be 20 MB or smaller.")
        if not data.startswith(b"%PDF-"):
            raise HTTPException(415, "The uploaded file is not a PDF.")
        async with app.state.processing:
            return await run_in_threadpool(analyze, data, filename)
    except PDFError as exc:
        raise HTTPException(422, str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Analysis failed")
        raise HTTPException(500, "Analysis failed. Check the server log for details.") from exc
    finally:
        await file.close()


@app.get("/api/history")
def history(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    return database.history(limit, offset)


@app.get("/api/analysis/{analysis_id}")
def get_analysis(analysis_id: str):
    result = database.get(analysis_id)
    if result is None:
        raise HTTPException(404, "Analysis not found.")
    return result
