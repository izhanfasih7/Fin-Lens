"""Illustrative data only; this is not an extracted company report."""
from .ratios import calculate_ratios
from .health import rule_rating, feature_values
from random import SystemRandom


def randomize_sample(result):
    rng = SystemRandom()
    previous = rng.randint(2200, 7400)
    revenues = (previous, round(previous * rng.uniform(.92, 1.22)))
    for slot, revenue in zip(('previous', 'current'), revenues):
        m = result['metrics']
        m['revenue'][slot] = revenue
        m['ebitda'][slot] = round(revenue * rng.uniform(.16, .28))
        m['finance_cost'][slot] = round(revenue * rng.uniform(.01, .025))
        m['depreciation'][slot] = round(revenue * rng.uniform(.025, .045))
        m['pbt'][slot] = m['ebitda'][slot] - m['finance_cost'][slot] - m['depreciation'][slot]
        m['tax'][slot] = round(m['pbt'][slot] * .25)
        m['pat'][slot] = m['pbt'][slot] - m['tax'][slot]
    ltm = result['metrics']['ebitda']['current'] * 4
    debt = round(ltm * rng.uniform(.3, .85))
    result['balance'] = {'net_debt': debt, 'ltm_ebitda': ltm, 'net_debt_to_ebitda': round(debt/ltm, 2)}
    result['ratios'] = calculate_ratios(result['metrics'], result['balance'])
    result['health'] = {'score': rng.randint(81, 93), 'rating': 'Illustrative score',
                        'method': 'illustrative', 'available_features': 5,
                        'reason': 'Random demo score, not a model prediction or assessment of the uploaded company.'}
    segments = {f'Sample segment {letter}': {} for letter in 'ABCDE'}
    for slot in ('previous', 'current'):
        total = result['metrics']['ebitda'][slot]
        values = [round(total * weight) for weight in (.3,.25,.2,.15)]
        values.append(total-sum(values))
        for pair, value in zip(segments.values(), values):
            pair[slot] = value
    result['segment_ebitda'] = segments
    result['periods'] = {'previous': 'Sample previous period', 'current': 'Sample current period'}
    result['data_origin'] = 'synthetic_demonstration'
    return result


def fallback_analysis(extracted=None, reason='Financial extraction was unavailable.'):
    """A separate, explicitly synthetic scenario; never fill gaps in real data."""
    result = demo_analysis()
    result['segment_ebitda'] = dict(zip(('Sample segment A','Sample segment B','Sample segment C','Sample segment D','Sample segment E'), result['segment_ebitda'].values()))
    result['periods'] = {'previous':'Sample previous period','current':'Sample current period'}
    result['is_fallback'] = True
    result['data_origin'] = 'synthetic_demonstration'
    result['extracted_report'] = extracted
    result['page_count'] = (extracted or {}).get('page_count')
    result['warnings'] = [reason, 'All displayed financial figures, segments, sentiment and ratings are illustrative sample data. They are not findings about the uploaded company. Available extraction is preserved separately in the JSON export.']
    return result


def demo_analysis():
    pairs = {"revenue": (100000, 120000), "ebitda": (36000, 41000),
             "finance_cost": (5000, 5000), "depreciation": (9000, 10000),
             "pbt": (10000, 18000), "tax": (3200, 4440), "pat": (6800, 13560)}
    metrics = {key: dict(zip(("previous", "current"), pair)) for key, pair in pairs.items()}
    balance = {"net_debt": 60000, "ltm_ebitda": 150000, "net_debt_to_ebitda": .4}
    ratios = calculate_ratios(metrics, balance)
    health = rule_rating(feature_values(ratios))
    health.update(reason="Illustrative ratio rules applied to invented figures.", available_features=5)
    result = {"id": "demo", "is_demo": True, "filename": "Illustrative company · quarterly results",
            "created_at": None, "page_count": None, "units": "INR crore",
            "periods": {"previous": "Q1 FY25", "current": "Q1 FY26"},
            "metrics": metrics, "balance": balance, "ratios": ratios, "health": health,
            "segment_ebitda": {key: dict(zip(("previous", "current"), pair)) for key, pair in
                              {"O2C": (12000, 13000), "E&P": (4000, 4500),
                               "Digital Services": (10000, 12500), "Retail": (8000, 9000),
                               "Others": (2000, 2000)}.items()},
            "sentiment": {"status": "ok", "model": "Illustrative sentiment", "gauge_score": 75,
                          "percentages": {"positive": 60, "neutral": 30, "negative": 10},
                          "top_positive": [{"sentence": "Digital services delivered strong growth this quarter.", "confidence": .94}],
                          "top_negative": [{"sentence": "Input cost pressures continued to affect margins.", "confidence": .88}],
                          "sentences_analyzed": 10, "sentences_total": 10,
                          "sentences_skipped": 0, "sentences_truncated": 0},
            "missing": [], "sources": {}, "commentary": [],
            "warnings": ["All figures and sentiment in this demo are invented for illustration. They are not Reliance results or model predictions."]}
    return randomize_sample(result)
