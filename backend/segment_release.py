"""Read quarterly EBITDA sections using the table's explicit date-group headers."""
import re

DATE = re.compile(r'(\d{1,2})(?:st|nd|rd|th)?\s+(Mar|Jun|Sep|Dec)[’\x27 ](\d{2,4})', re.I)


def recover_segments(text, tables):
    from .extraction import normalize, number, key_for, SEGMENTS, RUPEES
    if 'CONSOLIDATED SEGMENT INFORMATION' not in text.upper() or not RUPEES.search(text):
        return []
    for table in tables:
        if len(table) < 2:
            continue
        groups = [normalize(c) for c in table[0]]
        starts = [i for i,c in enumerate(groups) if c.lower() == 'quarter ended']
        if len(starts) != 1:
            continue
        start = starts[0]
        end = next((i for i in range(start+1,len(groups)) if groups[i]),len(groups))
        dates = [(i,DATE.fullmatch(normalize(c))) for i,c in enumerate(table[1])]
        dates = [(i,m) for i,m in dates if m]
        quarters = []
        for position,(i,m) in enumerate(dates):
            if start <= i < end:
                day,month,year=m.groups()
                q={'jun':1,'sep':2,'dec':3,'mar':4}[month.lower()]
                fy=int(year)%100+(q!=4)
                quarters.append((fy,q,position))
        if not quarters:
            continue
        current=max(quarters)
        previous=[a for a in quarters if a[:2]==(current[0]-1,current[1])]
        if len(previous)!=1:
            continue
        pair=[previous[0],current]
        rows=[]
        active=False
        for line in text.splitlines():
            if 'Segment Results (EBITDA)' in line:
                active=True
                continue
            if active and ('Segment Results (EBIT)' in line or 'Total' in line):
                break
            if not active:
                continue
            tokens=line.split()
            first=next((i for i,t in enumerate(tokens) if number(t) is not None),None)
            if first is None:
                continue
            label=' '.join(tokens[:first]).lstrip('- ').replace('*','')
            label=re.sub(r'\s*\(O2C\)$','',label)
            key=key_for(label,SEGMENTS)
            values=tokens[first:]
            if key and len(values)==len(dates) and all(number(v) is not None for v in values):
                rows.append([key,*(values[a[2]] for a in pair)])
        if rows:
            return [[['EBITDA',*(f'Q{q} FY{y:02d} Rs crore' for y,q,_ in pair)],*rows]]
    return []
