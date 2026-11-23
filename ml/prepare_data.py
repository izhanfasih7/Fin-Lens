"""Download a public Kaggle CSV and derive project-specific weak labels."""
import argparse
import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd
from backend.health import FEATURES, ROOT, rule_rating

SOURCE = "https://www.kaggle.com/datasets/rish59/financial-statements-of-major-companies2009-2023"
DOWNLOAD = "https://www.kaggle.com/api/v1/datasets/download/rish59/financial-statements-of-major-companies2009-2023"


def prepare(raw):
    frame = pd.read_csv(io.BytesIO(raw))
    frame.columns = frame.columns.str.strip()
    required = ["Company", "Year", "Revenue", "EBITDA", "Net Income"]
    if not set(required).issubset(frame.columns):
        raise ValueError(f"Dataset must contain {required}")
    frame = frame[required].copy()
    for key in required[1:]:
        frame[key] = pd.to_numeric(frame[key], errors="coerce")
    frame = frame.dropna().sort_values(["Company", "Year"])
    if frame.duplicated(["Company", "Year"]).any():
        raise ValueError("Duplicate company/year rows require manual review.")
    previous = frame.groupby("Company")[required[1:]].shift(1)
    adjacent = frame["Year"] - previous["Year"] == 1
    out = frame[["Company", "Year"]].rename(columns={"Company": "company", "Year": "year"})
    denominator = frame["Revenue"].where(frame["Revenue"] > 0)
    out["ebitda_margin_pct"] = frame["EBITDA"] / denominator * 100
    out["pat_margin_pct"] = frame["Net Income"] / denominator * 100
    for source, name in [("Revenue", "revenue"), ("EBITDA", "ebitda"), ("Net Income", "pat")]:
        base = previous[source].where(adjacent & (previous[source] > 0))
        out[f"{name}_growth_pct"] = (frame[source] - base) / base * 100
    out = out.replace([float("inf"), float("-inf")], float("nan"))
    out = out[out[FEATURES].notna().sum(axis=1) >= 4].copy()
    out["health_label"] = [rule_rating(row)["rating"] for row in out[FEATURES].to_dict("records")]
    out["label_source"] = "weak_ratio_rules_v1"
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-csv", type=Path, help="Use a manually downloaded Kaggle CSV")
    parser.add_argument("--output", type=Path, default=ROOT / "data/training/company_ratios.csv")
    args = parser.parse_args()
    if args.raw_csv:
        raw = args.raw_csv.read_bytes()
    else:
        with urllib.request.urlopen(DOWNLOAD, timeout=60) as response:
            archive = response.read(20 * 1024 * 1024 + 1)
        if len(archive) > 20 * 1024 * 1024:
            raise ValueError("Unexpected download size")
        with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
            member = zipped.getinfo("Financial Statements.csv")
            if member.file_size > 20 * 1024 * 1024:
                raise ValueError("Unexpected CSV size")
            raw = zipped.read(member)
    frame = prepare(raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False)
    metadata = {"source": SOURCE, "raw_sha256": hashlib.sha256(raw).hexdigest(),
                "rows": len(frame), "companies": int(frame.company.nunique()),
                "labels": frame.health_label.value_counts().to_dict(),
                "label_source": "weak_ratio_rules_v1",
                "limitations": "Rule-derived labels, annual US data; not verified credit ratings."}
    args.output.with_suffix(".source.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
