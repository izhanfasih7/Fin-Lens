"""Read split quarter/year headers in consolidated earnings-release tables."""
import re
from .layout import lines


def recover_release(page):
    from .extraction import number, RUPEES
    words = page.extract_words()
    grouped = lines(words)
    title = next((line for line in grouped if 'CONSOLIDATED FINANCIAL HIGHLIGHTS' in
                  ' '.join(w['text'] for w in line).upper()), None)
    if not title:
        return []
    start = title[0]['top']
    header = next((line for line in grouped if line[0]['top'] > start and
                   sum(bool(re.fullmatch(r'[1-4]Q', w['text'])) for w in line) >= 2), None)
    if not header:
        return []
    quarters = [w for w in header if re.fullmatch(r'[1-4]Q', w['text'])]
    years = [w for w in words if header[0]['top'] < w['top'] < header[0]['top']+25
             and re.fullmatch(r'FY\d{2,4}', w['text'])]
    unit_text = ' '.join(w['text'] for w in words if start < w['top'] < header[0]['top'])
    if not RUPEES.search(unit_text) or re.search(r'USD|\$', unit_text):
        return []
    anchors = []
    for q in quarters:
        matching = [y for y in years if abs(y['x1']-q['x1']) < 15]
        if len(matching) != 1:
            return []
        y = matching[0]
        anchors.append((int(y['text'][2:]) % 100, int(q['text'][0]), q['x1'], y['bottom']))
    current = max(anchors)
    previous = [a for a in anchors if a[:2] == (current[0]-1, current[1])]
    if len(previous) != 1:
        return []
    selected = [previous[0], current]
    gap = min(b[2]-a[2] for a,b in zip(anchors,anchors[1:]))
    tolerance = gap*.3
    label_right = min(a[2] for a in anchors)-gap*.65
    bottom = max(a[3] for a in anchors)
    rows = []
    for line in grouped:
        if line[0]['top'] <= bottom:
            continue
        if rows and re.match(r'^[*#]|^\d[QM]\s+FY', ' '.join(w['text'] for w in line)):
            break
        values = []
        for anchor in selected:
            found = [w for w in line if abs(w['x1']-anchor[2]) < tolerance
                     and (number(w['text']) is not None or w['text'] in ('-','—','–'))]
            values.append(found[0]['text'] if len(found)==1 else None)
        label_words = [w for w in line if w['x1'] < label_right]
        label = ' '.join(w['text'] for w in label_words)
        label = re.sub(r'^\d+\s+', '', label)
        if all(v is not None for v in values) and label:
            rows.append([label, *values])
        elif rows and label and not any(w['x0'] >= label_right for w in line):
            # Wrapped labels end before the following numerical row.
            rows[-1][0] += ' '+label
    return [[['Metric', *(f'Q{a[1]} FY{a[0]:02d} Rs crore' for a in selected)], *rows]]
