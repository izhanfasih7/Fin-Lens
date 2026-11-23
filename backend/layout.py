"""Recover header-aligned columns when PDF border detection merges a whole slide.

No page numbers or report amounts are hardcoded. A table needs two explicit period
or date anchors and unambiguous rupee columns before it can yield values.
"""
import re
import statistics

QUARTER = re.compile(r"Q[1-4]\s+FY\s*\d{2,4}", re.I)
DATE = re.compile(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[- ](\d{2,4})", re.I)
INR = re.compile(r"(?:₹|Rs\.?|INR)\s*(?:crore|cr)", re.I)
USD = re.compile(r"(?:\$|USD)\s*(?:Bn|billion)", re.I)
MONTHS = {name.lower(): i for i, name in enumerate(
    ('Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'), 1)}


def footnotes(page):
    """Separate small-print notes from adjacent, larger narrative columns."""
    words = page.extract_words(extra_attrs=['size'])
    if not words:
        return []
    body_size = statistics.median(w['size'] for w in words)
    small = [w for w in words if w['size'] < body_size*.75]
    texts = [' '.join(w['text'] for w in line) for line in lines(small)]
    return [text for text in texts if re.match(r'\d+\.\s', text) and any(
        word in text.lower() for word in ('exclude','inclusive','includes','others include'))]


def lines(words):
    result = []
    for word in sorted(words, key=lambda w: (w['top'], w['x0'])):
        if not result or abs(word['top'] - result[-1][0]['top']) > 3:
            result.append([word])
        else:
            result[-1].append(word)
    return [sorted(line, key=lambda w: w['x0']) for line in result]


def phrases(line, pattern):
    found, used = [], set()
    for i in range(len(line)):
        if i in used:
            continue
        for length in (3, 2, 1):
            chunk = line[i:i+length]
            text = ' '.join(w['text'] for w in chunk)
            if len(chunk) == length and pattern.fullmatch(text):
                found.append({'text': text, 'x': (chunk[0]['x0'] + chunk[-1]['x1']) / 2,
                              'top': min(w['top'] for w in chunk),
                              'bottom': max(w['bottom'] for w in chunk)})
                used.update(range(i, i+length))
                break
    return found


def recover_table(page):
    # Import at call time to keep the extraction dataclass independent of this helper.
    from .extraction import number, key_for, METRICS, SEGMENTS, BALANCE
    words = page.extract_words()
    grouped = lines(words)
    heading = ' '.join(w['text'] for line in grouped[:4] for w in line).lower()
    is_balance = 'strong balance sheet' in heading
    is_segments = 'segment performance' in heading or 'strong growth momentum across businesses' in heading
    if not (is_balance or is_segments or 'consolidated financial results' in heading):
        return [], None, None
    pattern = DATE if is_balance else QUARTER
    headers = [(line, phrases(line, pattern)) for line in grouped]
    headers = [(line, anchors) for line, anchors in headers if len(anchors) == 2]
    if len(headers) != 1:
        return [], None, None
    header_line, anchors = headers[0]
    header_top = min(a['top'] for a in anchors)
    header_bottom = max(a['bottom'] for a in anchors)
    nearby = [line for line in grouped if header_top-3 <= line[0]['top'] <= header_bottom+60]
    inr = [a for line in nearby for a in phrases(line, INR)]
    usd = [a for line in nearby for a in phrases(line, USD)]
    percentages = [dict(text='%', x=(w['x0']+w['x1'])/2, top=w['top'], bottom=w['bottom'])
                   for line in nearby for w in line if w['text'] == '%']
    if len(inr) == 2:
        inr.sort(key=lambda a: a['x'])
        # Each currency subcolumn must belong to a different period-header region.
        assignment = [min(range(2), key=lambda i: abs(a['x']-anchors[i]['x'])) for a in inr]
        if assignment != [0, 1]:
            return [], None, None
        selected = inr
        all_columns = sorted(inr + usd + percentages, key=lambda a: a['x'])
    elif len(inr) == 1 and inr[0]['x'] < anchors[0]['x'] and not usd:
        selected = anchors
        all_columns = sorted(anchors + percentages, key=lambda a: a['x'])
    else:
        return [], None, None
    gaps = [b['x']-a['x'] for a,b in zip(all_columns,all_columns[1:])]
    if not gaps or min(gaps) <= 0:
        return [], None, None
    tolerance = min(gaps) * .45
    label_right = selected[0]['x'] - tolerance
    numeric_rows = []
    for line in grouped:
        if line[0]['top'] <= header_bottom:
            continue
        values = []
        for anchor in selected:
            matches = [w for w in line if abs((w['x0']+w['x1'])/2-anchor['x']) < tolerance
                       and (number(w['text']) is not None or w['text'] in ('—','–','-'))]
            values.append(matches[0]['text'] if len(matches) == 1 else None)
        if all(v is not None for v in values):
            numeric_rows.append((statistics.mean(w['top'] for w in line
                                  if any(abs((w['x0']+w['x1'])/2-a['x'])<tolerance for a in selected)), values))
    if len(numeric_rows) < 2:
        return [], None, None
    spacing = statistics.median(b[0]-a[0] for a,b in zip(numeric_rows,numeric_rows[1:]))
    aliases = BALANCE if is_balance else SEGMENTS if is_segments else METRICS
    rows, last_y, total_ebitda = [], header_bottom, False
    for y, values in numeric_rows:
        label = ' '.join(w['text'] for line in grouped for w in line
                         if w['x1'] < label_right and y-spacing*.48 <= w['top'] < y+spacing*.48)
        if label.lower() == 'total ebitda':
            total_ebitda = True
        if key_for(label, aliases):
            rows.append([label, *values])
            last_y = max(last_y, y)
    if not rows or (is_segments and not total_ebitda):
        return [], None, None
    as_of = None
    if is_balance:
        def date_key(anchor):
            month, year = DATE.fullmatch(anchor['text']).groups()
            year = int(year)
            return (2000+year if year<100 else year, MONTHS[month.lower()])
        dates = [date_key(a) for a in anchors]
        if dates[0] == dates[1]:
            return [], None, None
        current = max(range(2), key=lambda i: dates[i])
        as_of = anchors[current]['text']
        table = [[row[0], row[current+1]] for row in rows]
    else:
        table = [['EBITDA' if is_segments else 'Metric',
                  *(a['text']+' Rs crore' for a in anchors)], *rows]
    # Exclude the recovered table from commentary, retaining nearby narrative text.
    right = all_columns[-1]['x'] + tolerance
    bottom = last_y + spacing*.55
    outside = [w for w in words if w['x0'] > right or w['top'] > bottom or w['bottom'] < header_top]
    commentary = '\n'.join(' '.join(w['text'] for w in line) for line in lines(outside))
    return [table], as_of, commentary
