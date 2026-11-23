"""Explicit one-time download; API requests never initiate a model download."""
from backend.sentiment import MODEL_ID, ROOT


def main():
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    path = ROOT / "models/finbert"
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID)
    path.mkdir(parents=True, exist_ok=True)
    tokenizer.save_pretrained(path)
    model.save_pretrained(path, safe_serialization=True)
    print(f"FinBERT ready at {path}")


if __name__ == "__main__":
    main()
