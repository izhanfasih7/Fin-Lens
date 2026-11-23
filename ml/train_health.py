"""Train, evaluate on held-out companies, and export a reproducible pipeline."""
import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline

from backend.health import FEATURES, LABELS, ROOT


def train(csv_path, output):
    frame = pd.read_csv(csv_path)
    required = set(FEATURES + ["company", "health_label", "label_source"])
    if not required.issubset(frame.columns):
        raise ValueError(f"Missing CSV columns: {sorted(required - set(frame.columns))}")
    if frame[["company", "health_label", "label_source"]].isna().any().any():
        raise ValueError("Company, label and label provenance must not be missing.")
    if set(frame.health_label) != set(LABELS) or frame.company.nunique() < 4:
        raise ValueError("Need all three labels and at least four distinct companies.")
    x = frame[FEATURES].apply(pd.to_numeric, errors="raise").replace([np.inf, -np.inf], np.nan)
    if (x.notna().sum(axis=1) < 4).any() or x.isna().all().any():
        raise ValueError("Each row needs at least four features and no feature can be entirely missing.")
    y = frame.health_label
    train_ids, test_ids = next(GroupShuffleSplit(n_splits=1, test_size=.25, random_state=42)
                              .split(x, y, groups=frame.company))
    if set(y.iloc[train_ids]) != set(LABELS):
        raise ValueError("Training split lacks a class. Add more companies; do not tune on test scores.")
    pipeline = Pipeline([("impute", SimpleImputer(strategy="median", add_indicator=True)),
                         ("classifier", RandomForestClassifier(n_estimators=200, max_depth=6,
                          min_samples_leaf=2, class_weight="balanced", random_state=42, n_jobs=1))])
    # Fit preprocessing on training rows only; the test companies never enter fitting.
    pipeline.fit(x.iloc[train_ids].to_numpy(), y.iloc[train_ids])
    predicted = pipeline.predict(x.iloc[test_ids].to_numpy())
    report = {"accuracy": accuracy_score(y.iloc[test_ids], predicted),
              "macro_f1": f1_score(y.iloc[test_ids], predicted, labels=LABELS, average="macro", zero_division=0),
              "confusion_matrix_labels": LABELS,
              "confusion_matrix": confusion_matrix(y.iloc[test_ids], predicted, labels=LABELS).tolist(),
              "classification_report": classification_report(y.iloc[test_ids], predicted, labels=LABELS,
                                                              output_dict=True, zero_division=0),
              "train_rows": len(train_ids), "test_rows": len(test_ids),
              "train_companies": sorted(frame.company.iloc[train_ids].unique().tolist()),
              "test_companies": sorted(frame.company.iloc[test_ids].unique().tolist()),
              "seed": 42, "sklearn_version": sklearn.__version__,
              "csv_sha256": hashlib.sha256(Path(csv_path).read_bytes()).hexdigest(),
              "label_source": sorted(frame.label_source.unique().tolist()),
              "limitations": "Weak labels measure reproduction of rules, not real-world health accuracy. Annual US data may not generalize to Indian quarterly results."}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"schema_version": 1, "features": FEATURES, "model": pipeline,
                 "label_source": report["label_source"], "limitations": report["limitations"],
                 "sklearn_version": sklearn.__version__}, output)
    output.with_suffix(".metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=ROOT / "data/training/company_ratios.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "models/health.joblib")
    args = parser.parse_args()
    print(json.dumps(train(args.csv, args.output), indent=2))


if __name__ == "__main__":
    main()
