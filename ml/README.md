# Deliverable 4: sentiment and health ML

## Run from the project root

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.\.venv\Scripts\python.exe -m ml.prepare_data
.\.venv\Scripts\python.exe -m ml.train_health
.\.venv\Scripts\python.exe -m ml.download_finbert
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

Stop any previous server before starting another on port 8000. New analyses include
`health` and `sentiment`; existing SQLite records remain as originally saved.
Open http://127.0.0.1:8000/docs to upload a report. ML runs locally, without uploading
report text to Hugging Face. Installing dependencies and downloading weights requires
internet access and several hundred MB of disk space.

## Health model and data

Source: [Financial Statements of Major Companies (2009–2023), Kaggle](https://www.kaggle.com/datasets/rish59/financial-statements-of-major-companies2009-2023).
The preparation script downloads the public archive, reads only its CSV, strips header
whitespace, validates company/year uniqueness, and produces:

- `data/training/company_ratios.csv`: five supported ratios and labels.
- `data/training/company_ratios.source.json`: source URL, SHA-256, counts and provenance.

If the public download becomes unavailable, download the CSV from Kaggle and run
`python -m ml.prepare_data --raw-csv "C:\path\Financial Statements.csv"`.

Features are EBITDA margin, PAT margin, revenue growth, EBITDA growth and PAT growth.
Margins and growth are expressed in percentage points (11.3 means 11.3%). Growth
requires consecutive years and a positive prior value. Ratios avoid currency-scale
differences, but annual US data is still a poor proxy for Indian quarterly reports.
The dataset lacks finance cost and net debt, so these are not training features.

**This dataset has no verified Good/Average/Risky labels.** We explicitly create
weak labels using these educational assumptions:

| Feature | 0 points | 50 points | 100 points |
| --- | --- | --- | --- |
| EBITDA margin | < 0% | 0% to < 15% | >= 15% |
| PAT margin | < 0% | 0% to < 10% | >= 10% |
| Each YoY growth | < 0% | 0% to < 10% | >= 10% |

The available-feature mean gives Good at >=70, Average at >=40, otherwise Risky.
Missing ratios are excluded. Fewer than two ratios gives a null rating and score.
These are project choices, not industry-standard rating thresholds. For a rigorous
study, obtain independent expert labels or outcomes and repeat evaluation.

`train_health.py` fits a median imputer and Random Forest on training companies only.
One fixed group split (seed 42, 25% of companies held out) prevents the same company
appearing on both sides. The imputer is inside the pipeline, avoiding preprocessing
leakage. The script writes accuracy, macro F1, a classification report, confusion
matrix (rows=true, columns=predicted), company lists and training versions to
`models/health.metrics.json`; `models/health.joblib` contains the fitted pipeline.
The exported model is the evaluated training-split model, not a full-data refit.

The completed run used 141 rows from 12 companies: 109 training rows and 32 test
rows. Accuracy was **0.84375**, macro F1 **0.728327**. Held-out companies were AAPL,
PCG and PYPL. The confusion matrix in Risky/Average/Good order was:

```text
1  1   0
1  8   1
0  2  18
```

Only two Risky examples appear in the test set. These metrics therefore have high
uncertainty, especially for the Risky class. `requirements-lock.txt` records the
installed package versions for reproducing this environment.

Accuracy here measures **agreement with the label rules**, not financial health or
bankruptcy prediction. The target is constructed from the same features: that
circularity is deliberate for a beginner demonstration and invalid as independent
financial validation. A held-out class may have little or zero support; inspect the
per-class report rather than quoting accuracy alone.

At inference, at least four of five ratios are required for ML. Otherwise the API
uses the rules and reports `method: rule_based`; with fewer than two usable ratios
it reports `insufficient_data`. Missing/unloadable models also fall back to rules.
The ML rating is the most probable class. The 0–100 display score is
`100 * P(Good) + 50 * P(Average)`; it is not a calibrated probability and need not
match the rule thresholds. Only load joblib artifacts you trained and trust.

## FinBERT

[ProsusAI/finbert](https://huggingface.co/ProsusAI/finbert) is a pretrained financial
text classifier with positive, neutral and negative outputs. The setup script caches
the tokenizer and model locally and saves weights as safetensors. There is no
FinBERT retraining in this project.

The API deduplicates commentary sentences, processes up to 240 in batches of eight,
and reports skipped sentences and 512-token truncation. Percentages are the shares
of sentences assigned to each class. The gauge uses mean class probabilities:
`50 * (1 + mean_positive - mean_negative)`. Zero is negative, 50 neutral, 100 positive.
Top lists include up to three sentences actually assigned to that class, ordered
by confidence; a class with no matching sentences has an empty list.

Model weights are loaded once per server process, on first use. The API never
downloads a model during upload. If weights/dependencies are unavailable, sentiment
is explicitly `unavailable` with null percentages/score; it does not invent neutral
results. Empty commentary returns `no_commentary`. English text is expected.

Slide-text extraction is approximate: wrapped bullets may be separated, tables may
leak into commentary, and company presentations have promotional bias. FinBERT
confidence is not a guarantee of interpretation. No claim of evaluation on the
unprovided Reliance PDF is made.

## Files and configuration

- `backend/health.py`: feature contract, rules and trained-model inference.
- `backend/sentiment.py`: sentence splitting, local FinBERT and output aggregation.
- `ml/prepare_data.py`: real public data preparation and transparent weak labels.
- `ml/train_health.py`: training, metrics and joblib export.
- `ml/download_finbert.py`: one-time model setup.
- `tests/test_ml.py`: missing data, group split, training round trip and sentiment tests.

Optional environment variables: `FINLENS_HEALTH_MODEL` overrides the joblib path;
`FINLENS_FINBERT_DIR` overrides the local FinBERT folder. Restart the server after
replacing FinBERT weights. Defaults resolve relative to this repository, not the
shell working directory.
