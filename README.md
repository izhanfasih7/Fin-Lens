# FinLens — Financial Report Analyzer

FinLens is a local educational web application for reviewing financial PDFs. It extracts supported quarterly figures and source pages, calculates ratios, displays charts, analyzes management sentiment with optional FinBERT, and saves analyses in SQLite.

## Features and limits
- PDF upload, financial/segment comparisons, ratio calculations, JSON export and history.
- Supported Reliance presentation and earnings-release layouts; sourced overview excerpts from results FAQs.
- Optional locally trained health classifier, with ratio-rule fallback.
- Explicitly labelled synthetic previews when extraction cannot recover financial amounts. Sample amounts are under INR 10,000 crore and demo scores are randomly selected from 81–93; these are NOT model accuracy or company assessments. Real extracted results are not capped or randomized.
- PDF limit: 20 MB / 200 pages. No OCR. FinBERT examines up to 240 commentary sentences, not every word. Arbitrary PDFs and financial accuracy are not guaranteed.

## Technology
Python 3.12, FastAPI/Uvicorn, SQLite, pdfplumber/PyMuPDF; HTML/CSS/JavaScript and Chart.js; optional PyTorch/Transformers/FinBERT and scikit-learn. No Node.js, npm, frontend build, paid API key or external database is required.

## Quick start: Windows (PowerShell)
Install Python 3.12 x64, extract the entire folder, and open PowerShell in it:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -X utf8 -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -X utf8 -m pip check
.\.venv\Scripts\python.exe -m ml.download_finbert
.\.venv\Scripts\python.exe -X utf8 run.py
```

Open http://127.0.0.1:8000/. Keep the terminal open; Ctrl+C stops it. After setup, double-click `start.cmd`. If the port is occupied, use `run.py --port 8001`. The localhost URL works only on the computer running the server.

## macOS / Linux
Python 3.12 and the venv module must be installed:

```sh
python3.12 -m venv .venv
.venv/bin/python -X utf8 -m pip install -r requirements.txt
.venv/bin/python -X utf8 -m pip check
.venv/bin/python -m ml.download_finbert
.venv/bin/python run.py
```

The exact lock is a Windows Python 3.12 version snapshot, not a universal cross-platform lock. If a pinned wheel is unavailable, try `requirements-ml.txt` (compatible version ranges), then run tests. This alternative may produce different ML behavior. macOS/Linux have not been validated here.

## Smaller installation
`requirements-backend.txt` installs just the web/PDF stack. You can skip FinBERT and run the same launcher; sentiment will be unavailable and health uses ratio rules if the classifier cannot load. The full test suite needs the ML packages.

## Models and data
- `models/health.joblib` is the existing small locally trained classifier; its evaluation is in `models/health.metrics.json`. Use the pinned environment for compatibility. Load only trusted joblib files.
- FinBERT weights are NOT included (~438 MB, above normal GitHub file limits). `python -m ml.download_finbert` downloads the public `ProsusAI/finbert` model once from Hugging Face. No API key is required for normal public access. Internet access and several GB of disk space are needed for installation/model downloads.
- To rebuild the health classifier: `python -m ml.prepare_data`, then `python -m ml.train_health`. This requires the public Kaggle dataset; see `ml/README.md` for its source and manual CSV alternative. Labels are rule-derived and are not independent financial risk ratings.
- SQLite initializes automatically at `data/finlens.sqlite3`. No server, migration command, credentials or existing history are needed. `backend/database.py` contains the schema.
- No uploaded PDFs, personal analysis history, training CSVs or private credentials are included. Tests contain limited financial-table fixtures; no complete company reports are bundled.

## Configuration
No environment variables are required. `.env.example` documents optional overrides. The app does NOT automatically load `.env` files. Set variables in the shell before starting, for example:

```powershell
$env:FINLENS_DB = 'C:\FinLensData\finlens.sqlite3'
.\.venv\Scripts\python.exe run.py
```

Use absolute paths for `FINLENS_HEALTH_MODEL` and `FINLENS_FINBERT_DIR` if overriding their defaults.

## Development and tests
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe run.py --reload
```
Four optional full-PDF tests skip unless their external sample files are supplied with `FINLENS_SAMPLE_PDF` / `FINLENS_FY27_PDF`. Expected error logs in mocked fallback tests do not imply test failures. `/docs` provides interactive API documentation; `/api/analyze` accepts a PDF, `/api/history` lists saved analyses, and `/api/analysis/{id}` returns JSON.

## Project structure
- `frontend/`: pages, scripts, styles, profile image and bundled vendor assets.
- `backend/`: extraction, ratios, inference, API and database schema.
- `ml/`: model download, dataset preparation and training scripts.
- `models/`: health classifier and evaluation; FinBERT downloaded separately.
- `tests/`: automated tests and limited source-table fixtures.
- `run.py`, `start.cmd`: startup helpers.
- `requirements*.txt`: pinned installation and optional lightweight/range manifests.
- `ASSET-MANIFEST.json`, `THIRD_PARTY.md`: asset provenance and licensing notes.
- `VERIFICATION.md`: exact verification performed and remaining limitations.

## Share or publish source
Create an empty GitHub repository, then use GitHub Desktop → Add local repository → Create repository here, selecting this folder. Review the files before publishing. There is no inherited Git history or remote. Do not upload `.venv`, `data`, downloaded FinBERT, secrets or PDFs. GitHub hosts this source; GitHub Pages cannot run the Python backend.

The About Us name, photo and public profile links are intentionally retained. Email and phone are placeholders. Review third-party asset and fixture rights before choosing an open-source license; no license for your original code has been imposed. See `THIRD_PARTY.md`.

The original website was not modified during packaging. Older implementation notes are retained in `docs/history`; this README and SETUP.md supersede their setup instructions.
