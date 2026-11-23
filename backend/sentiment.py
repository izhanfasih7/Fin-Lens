"""Local FinBERT inference with explicit unavailable states and bounded input."""
import logging
import os
import re
import threading
from functools import lru_cache
from pathlib import Path

MODEL_ID = "ProsusAI/finbert"
ROOT = Path(__file__).resolve().parents[1]
LOCK = threading.Lock()
log = logging.getLogger(__name__)


def split_sentences(commentary):
    result = []
    seen = set()
    for paragraph in commentary:
        # The extractor already separates bullets; retain decimal points in numbers.
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'])|[\r\n]+", paragraph):
            sentence = re.sub(r"\s+", " ", sentence).strip(" •\t-–")
            if len(sentence.split()) >= 3 and sentence.casefold() not in seen:
                result.append(sentence)
                seen.add(sentence.casefold())
    return result


@lru_cache(maxsize=1)
def load_model(path):
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(path, local_files_only=True,
                                                               use_safetensors=True)
    torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
    model.eval()
    return tokenizer, model


def summarize_predictions(predictions, total, truncated):
    labels = ("positive", "neutral", "negative")
    counts = {label: sum(p["label"] == label for p in predictions) for label in labels}
    percentages = {label: round(100 * counts[label] / len(predictions), 2) for label in labels}
    mean = {label: sum(p["probabilities"][label] for p in predictions) / len(predictions)
            for label in labels}
    top = {label: sorted((p for p in predictions if p["label"] == label),
                        key=lambda p: p["confidence"], reverse=True)[:3]
           for label in ("positive", "negative")}
    return {"status": "ok", "model": MODEL_ID, "percentages": percentages,
            "gauge_score": round(50 * (1 + mean["positive"] - mean["negative"]), 1),
            "gauge_meaning": "0 negative, 50 neutral, 100 positive; averaged class probabilities.",
            "percentages_meaning": "Share of analyzed sentences assigned to each class.",
            "top_positive": top["positive"], "top_negative": top["negative"],
            "sentences_analyzed": len(predictions), "sentences_total": total,
            "sentences_skipped": total - len(predictions), "sentences_truncated": truncated}


def analyze_sentiment(commentary):
    sentences = split_sentences(commentary)
    empty = {"model": MODEL_ID, "percentages": None, "gauge_score": None,
             "top_positive": [], "top_negative": [], "sentences_analyzed": 0,
             "sentences_total": len(sentences)}
    if not sentences:
        return {**empty, "status": "no_commentary", "reason": "No usable commentary found."}
    path = Path(os.environ.get("FINLENS_FINBERT_DIR", str(ROOT / "models/finbert")))
    if not path.is_dir():
        return {**empty, "status": "unavailable",
                "reason": "Run python -m ml.download_finbert to install local model weights."}
    try:
        import torch
        with LOCK:
            tokenizer, model = load_model(str(path))
            predictions, truncated = [], 0
            # Bound CPU work; report skipped sentences explicitly rather than hiding sampling.
            selected = sentences[:240]
            labels = [model.config.id2label[i].lower() for i in range(model.config.num_labels)]
            if set(labels) != {"positive", "negative", "neutral"}:
                raise ValueError("Unexpected FinBERT labels")
            for start in range(0, len(selected), 8):
                batch = selected[start:start + 8]
                truncated += sum(len(tokenizer.encode(s, truncation=False)) > 512 for s in batch)
                inputs = tokenizer(batch, padding=True, truncation=True, max_length=512,
                                   return_tensors="pt")
                with torch.inference_mode():
                    scores = torch.softmax(model(**inputs).logits, dim=-1).tolist()
                for sentence, scores_row in zip(batch, scores):
                    probabilities = dict(zip(labels, scores_row))
                    label = max(probabilities, key=probabilities.get)
                    predictions.append({"sentence": sentence, "label": label,
                                        "confidence": round(probabilities[label], 4),
                                        "probabilities": probabilities})
            return summarize_predictions(predictions, len(sentences), truncated)
    except Exception:
        log.exception("FinBERT inference unavailable")
        return {**empty, "status": "unavailable",
                "reason": "FinBERT could not run. Check dependencies and server logs."}
