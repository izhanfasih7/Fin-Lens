"""Educational health classification; thresholds are project assumptions."""
import logging
import math
import os
from pathlib import Path

FEATURES = ["ebitda_margin_pct", "pat_margin_pct", "revenue_growth_pct",
            "ebitda_growth_pct", "pat_growth_pct"]
LABELS = ["Risky", "Average", "Good"]
ROOT = Path(__file__).resolve().parents[1]
log = logging.getLogger(__name__)


def feature_values(ratios):
    current = ratios.get("current", {})
    growth = ratios.get("yoy_growth_pct", {})
    return {"ebitda_margin_pct": current.get("ebitda_margin_pct"),
            "pat_margin_pct": current.get("pat_margin_pct"),
            **{f"{key}_growth_pct": growth.get(key) for key in ("revenue", "ebitda", "pat")}}


def finite(value):
    return isinstance(value, (float, int)) and math.isfinite(value)


def rule_rating(values):
    """Each available ratio earns 0, 50 or 100 points; never fill missing with zero."""
    thresholds = {"ebitda_margin_pct": (0, 15), "pat_margin_pct": (0, 10),
                  "revenue_growth_pct": (0, 10), "ebitda_growth_pct": (0, 10),
                  "pat_growth_pct": (0, 10)}
    points = {}
    for key, (low, high) in thresholds.items():
        value = values.get(key)
        if finite(value):
            points[key] = 0 if value < low else 100 if value >= high else 50
    if len(points) < 2:
        return {"rating": None, "score": None, "method": "insufficient_data",
                "reason": "At least two supported ratios are required.", "components": points}
    score = round(sum(points.values()) / len(points), 1)
    return {"rating": "Good" if score >= 70 else "Average" if score >= 40 else "Risky",
            "score": score, "method": "rule_based", "components": points}


def predict_health(ratios):
    values = feature_values(ratios)
    missing = [key for key in FEATURES if not finite(values[key])]
    fallback = rule_rating(values)
    fallback.update(missing_features=missing, available_features=len(FEATURES) - len(missing),
                    score_meaning="Educational ratio score, not a default probability.")
    if len(missing) > 1:
        fallback["reason"] = "Too few ratios for the model; using available ratios only."
        return fallback
    path = Path(os.environ.get("FINLENS_HEALTH_MODEL", str(ROOT / "models/health.joblib")))
    if not path.is_file():
        fallback["reason"] = "No trained model found."
        return fallback
    try:
        import joblib
        import numpy as np
        # Load only the locally trained artifact; there is no model upload endpoint.
        artifact = joblib.load(path)
        if artifact["features"] != FEATURES or artifact["schema_version"] != 1:
            raise ValueError("Incompatible feature schema")
        model = artifact["model"]
        if set(model.classes_) != set(LABELS):
            raise ValueError("Unexpected model labels")
        row = [[values[key] if finite(values[key]) else np.nan for key in FEATURES]]
        probabilities = dict(zip(model.classes_, map(float, model.predict_proba(row)[0])))
        score = 100 * probabilities["Good"] + 50 * probabilities["Average"]
        return {"rating": max(probabilities, key=probabilities.get), "score": round(score, 1),
                "method": "random_forest", "probabilities": probabilities,
                "missing_features": missing, "available_features": len(FEATURES) - len(missing),
                "label_source": artifact["label_source"],
                "score_meaning": "100 × P(Good) + 50 × P(Average); not calibrated financial risk.",
                "limitations": artifact["limitations"]}
    except Exception:
        log.exception("Health model failed; using rules")
        fallback["reason"] = "Model could not be loaded or evaluated; using ratio rules."
        return fallback
