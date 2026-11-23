"""Ratios are percentages unless the key ends in _x. Missing stays None."""


def divide(numerator, denominator, multiplier=1):
    if numerator is None or denominator in (None, 0):
        return None
    return round(numerator / denominator * multiplier, 2)


def calculate_ratios(metrics, balance):
    result = {}
    for period in ("previous", "current"):
        values = {key: value[period] for key, value in metrics.items()}
        result[period] = {
            "ebitda_margin_pct": divide(values["ebitda"], values["revenue"], 100),
            "pbt_margin_pct": divide(values["pbt"], values["revenue"], 100),
            "pat_margin_pct": divide(values["pat"], values["revenue"], 100),
            "effective_tax_rate_pct": divide(values["tax"], values["pbt"], 100),
            "interest_coverage_x": divide(values["ebitda"], values["finance_cost"]),
        }
    result["yoy_growth_pct"] = {}
    for key in ("revenue", "ebitda", "pat"):
        old, new = metrics[key]["previous"], metrics[key]["current"]
        # A non-positive base makes a conventional growth percentage misleading.
        result["yoy_growth_pct"][key] = (
            divide(new - old, old, 100)
            if old is not None and old > 0 and new is not None else None
        )
    reported = balance["net_debt_to_ebitda"]
    result["net_debt_to_ebitda_x"] = (
        reported if reported is not None
        else divide(balance["net_debt"], balance["ltm_ebitda"])
    )
    return result
