"""Conservative, auditable extraction. Ambiguous rows are deliberately left null.

Tables must identify their periods and rupee-crore units. No fixed slide numbers.
This is a baseline parser, not a claim of validation on an unavailable sample.
"""
import io
import re
from dataclasses import dataclass, field

METRICS = {
    "revenue": r"(?:revenue(?: from operations)?|gross revenue|total revenue)",
    "ebitda": r"ebitda",
    "finance_cost": r"finance costs?|interest costs?",
    "depreciation": r"depreciation(?: and amorti[sz]ation)?",
    "pbt": r"pbt|profit before tax",
    "tax": r"tax|tax expenses?|total tax",
    "pat": r"pat|profit after tax|profit for the (?:period|quarter|year)",
}
BALANCE = {
    "net_debt": r"net debt",
    "ltm_ebitda": r"ltm ebitda|ebitda \(ltm\)",
    "net_debt_to_ebitda": r"net debt\s*(?:/|to)\s*(?:ltm )?ebitda(?:\s*\(x\))?",
}
SEGMENTS = {
    "O2C": r"o2c|oil[ -]to[ -]chemicals",
    "E&P": r"e\s*&\s*p|exploration (?:and|&) production|oil (?:and|&) gas",
    "Digital Services": r"digital services|jio platforms",
    "Retail": r"retail|reliance retail",
    "Others": r"others",
}
PERIOD = re.compile(r"\bQ([1-4])\s*[-/]?\s*FY\s*['’]?(\d{2,4})\b", re.I)
RUPEES = re.compile(r"(?:rs\.?|inr|₹|rupees)\s*\.?\s*(?:in\s+)?(?:crore|cr\b)", re.I)


@dataclass
class Page:
    number: int
    text: str
    tables: list = field(default_factory=list)
    layout_tables: list = field(default_factory=list)
    balance_as_of: str | None = None
    commentary_text: str | None = None
    notes: list = field(default_factory=list)


class PDFError(ValueError):
    pass


def normalize(text):
    return re.sub(r"\s+", " ", str("" if text is None else text).replace("\u00a0", " ")).strip()


def number(text):
    """Do not reinterpret percentages, currency conversions, or footnote digits."""
    value = normalize(text)
    value = re.sub(r"[*†‡¹²³⁴⁵⁶⁷⁸⁹↑↓]", "", value).strip()
    if value in ("", "-", "–", "—", "NA", "N/A") or "%" in value:
        return None
    negative = value.startswith("(") and value.endswith(")")
    if negative:
        value = value[1:-1].strip()
    value = re.sub(r"[xX]$", "", value).strip()
    if not re.fullmatch(r"[+-]?(?:\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d+)?", value):
        return None
    parsed = float(value.replace(",", ""))
    return -parsed if negative else parsed


def read_pdf(data):
    import pdfplumber
    import pymupdf as fitz

    pages, warnings = [], []
    try:
        fallback = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise PDFError("Cannot open this PDF. It may be corrupt.") from exc
    with fallback:
        if fallback.needs_pass:
            raise PDFError("Password-protected PDFs are not supported.")
        if len(fallback) > 200:
            raise PDFError("Use a PDF with 200 pages or fewer.")
        try:
            primary = pdfplumber.open(io.BytesIO(data))
        except Exception:
            primary = None
            warnings.append("pdfplumber failed; using PyMuPDF text extraction.")
        try:
            for index, backup_page in enumerate(fallback):
                text, tables = "", []
                recovered, as_of, commentary = [], None, None
                notes = []
                if primary:
                    try:
                        page = primary.pages[index]
                        text = page.extract_text() or ""
                        tables = page.extract_tables() or []
                        if not tables:
                            tables = page.extract_tables({
                                "vertical_strategy": "text", "horizontal_strategy": "text"
                            }) or []
                        from .layout import recover_table, footnotes
                        recovered, as_of, commentary = recover_table(page)
                        from .release_layout import recover_release
                        recovered = recover_release(page) or recovered
                        if recovered:
                            notes = footnotes(page)
                    except Exception:
                        warnings.append(f"Page {index + 1}: primary extraction failed.")
                if not text.strip():
                    text = backup_page.get_text("text")
                pages.append(Page(index + 1, text, tables, recovered, as_of, commentary, notes))
        finally:
            if primary:
                primary.close()
    if not any(page.text.strip() for page in pages):
        raise PDFError("No selectable text found. OCR is required for scanned PDFs.")
    return pages, warnings


def periods_in(text):
    return [f"Q{q} FY{int(y) % 100:02d}" for q, y in PERIOD.findall(text)]


def key_for(label, aliases):
    clean = normalize(re.sub(r"[*†‡¹²³⁴⁵⁶⁷⁸⁹]", "", label)).lower().rstrip(":")
    return next((key for key, pattern in aliases.items()
                 if re.fullmatch(pattern, clean, re.I)), None)


def extract_pages(pages):
    candidates, warnings = {}, []
    period_pairs = set()

    def add(path, value, page, label, rank=1):
        if value is not None:
            candidates.setdefault(path, []).append((rank, value, page, label))

    context = None
    for page in pages:
        low = page.text.lower()
        from .segment_release import recover_segments
        segment_tables = recover_segments(page.text, page.tables)
        title = " ".join(page.text.splitlines()[:4]).lower()
        release = 'consolidated financial highlights' in low
        consolidated = "consolidated financial results" in low or release
        balance_page = "strong balance sheet" in low
        segment_summary = (bool(segment_tables) or "strong growth momentum across businesses" in low or
                           ("segment performance" in title and "total ebitda" in low))
        if consolidated or balance_page or segment_summary:
            context = None
        else:
            matches = [name for name, pattern in SEGMENTS.items() if re.search(pattern, title, re.I)]
            if len(matches) == 1:
                context = matches[0]
        if not (consolidated or balance_page or segment_summary or
                (context and "financial performance" in low)):
            continue
        page_rupees = bool(RUPEES.search(page.text))
        page_mixed = bool(re.search(r"\$|usd|\bbn\b|billion", low))

        # Text rows are a fallback only. Exact token/column counts are required.
        text_rows = []
        for line in page.text.splitlines():
            tokens = re.split(r"\s+", line.strip())
            first = next((i for i, token in enumerate(tokens)
                          if number(token) is not None or token in ("–", "-", "—")), None)
            if PERIOD.search(line):
                ps = periods_in(line)
                if len(ps) >= 2:
                    text_rows.append(["Metric", *ps])
            elif first is not None and first > 0:
                text_rows.append([" ".join(tokens[:first]), *tokens[first:]])

        if segment_tables:
            warnings.append(f'Page {page.number}: segment EBITDA uses the statutory segment disclosure; it excludes unallocated group items and may not sum to consolidated EBITDA.')
        for table, rank in ([(t, 3) for t in segment_tables + page.layout_tables] +
                            [(t, 2) for t in page.tables] + [(text_rows, 1)]):
            columns = {}
            usable = False
            # A segment revenue table is not a segment EBITDA table.
            segment_ebitda_table = any("ebitda" in normalize(cell).lower()
                                      for row in table[:3] for cell in row)
            for row in table:
                cells = [normalize(cell) for cell in row]
                found = {i: periods_in(cell)[0] for i, cell in enumerate(cells)
                         if len(periods_in(cell)) == 1}
                if len(found) >= 2:
                    columns = found
                    unique = set(found.values())
                    # Only an explicit same-quarter, consecutive-year comparison is YoY.
                    ordered = sorted(unique, key=lambda p: int(p[-2:]))
                    usable = (len(ordered) == 2 and ordered[0][:2] == ordered[1][:2]
                              and int(ordered[1][-2:]) - int(ordered[0][-2:]) == 1)
                    # Duplicate currency subcolumns require explicitly labelled INR cells.
                    if len(found) != 2:
                        columns = {i: p for i, p in found.items() if RUPEES.search(cells[i])}
                    explicit_units = all(RUPEES.search(cells[i]) for i in columns)
                    usable = usable and len(columns) == 2 and (
                        explicit_units or (page_rupees and not page_mixed))
                    if usable and consolidated:
                        period_pairs.add(tuple(ordered))
                    continue
                if not cells:
                    continue
                label = cells[0]
                if usable and all(i < len(cells) for i in columns):
                    # Reject text rows with extra values (e.g. an unlabelled YoY column).
                    if rank == 1 and len(cells) != max(columns) + 1:
                        continue
                    aliases = METRICS if consolidated else SEGMENTS if segment_summary else {"ebitda": r"ebitda"}
                    key = key_for(label, aliases)
                    combined_pat = release and bool(re.fullmatch(
                        r'profit after tax and share of profit/\(loss\) of associates & jvs', label, re.I))
                    if combined_pat:
                        key = 'pat'
                    if key and (not segment_summary or segment_ebitda_table):
                        for i, period in columns.items():
                            path = ("metric", key, period) if consolidated else (
                                "segment", key if segment_summary else context, period)
                            # Prefer the report's consolidated segment summary to
                            # individual subsidiary/segment financial slides.
                            add(path, number(cells[i]), page.number, label,
                                rank + 3 if segment_summary or combined_pat else rank)
                    if release and rank == 3:
                        balance_key = key_for(label, BALANCE)
                        latest = max(columns, key=lambda i: int(columns[i][-2:]))
                        if balance_key == 'net_debt':
                            add(('balance', balance_key), number(cells[latest]), page.number, label, rank)
                        if balance_key == 'net_debt_to_ebitda' and re.search(r'annuali[sz]ed', low):
                            add(('reported', 'annualized_leverage'), number(cells[latest]), page.number, label, rank)
                if balance_page:
                    key = key_for(label, BALANCE)
                    if key and len(cells) == 2 and (
                        key == "net_debt_to_ebitda" or rank == 3 or (page_rupees and not page_mixed)):
                        add(("balance", key), number(cells[1]), page.number, label, rank)

    periods = {"previous": None, "current": None}
    if len(period_pairs) == 1:
        periods = dict(zip(("previous", "current"), next(iter(period_pairs))))
    else:
        warnings.append("A unique consolidated YoY period pair could not be identified.")
    sources, missing = {}, []

    def choose(path, output_key):
        options = candidates.get(path, [])
        if options:
            best = max(item[0] for item in options)
            options = [item for item in options if item[0] == best]
            if len({item[1] for item in options}) == 1:
                sources[output_key] = [{"page": item[2], "label": item[3]} for item in options]
                return options[0][1]
            warnings.append(f"Conflicting values for {output_key}; left null.")
        missing.append(output_key)
        return None

    metrics = {key: {slot: choose(("metric", key, period), f"{key}.{slot}")
                     for slot, period in periods.items()} for key in METRICS}
    segments = {key: {slot: choose(("segment", key, period), f"segments.{key}.{slot}")
                      for slot, period in periods.items()} for key in SEGMENTS}
    balance = {key: choose(("balance", key), key) for key in BALANCE}
    annualized = choose(('reported', 'annualized_leverage'), 'annualized_net_debt_to_ebitda') if ('reported', 'annualized_leverage') in candidates else None
    for page in pages:
        if 'consolidated financial highlights' in page.text.lower():
            for line in page.text.splitlines():
                if re.search(r'excludes.*listed investments|inclusive of.*|annuali[sz]ed', line, re.I):
                    warnings.append(f'Page {page.number} note: {normalize(line)}')
    if any('and share of' in s['label'].lower() for s in sources.get('pat.current', [])):
        warnings.append('PAT includes the share of profit/(loss) of associates and joint ventures, as reported in the consolidated highlights.')
    # Keep commentary for the FinBERT delivery; avoid predominantly numerical rows.
    commentary = []
    for page in pages:
        for line in (page.commentary_text if page.commentary_text is not None else page.text).splitlines():
            line = normalize(line)
            if len(line.split()) >= 6 and sum(c.isdigit() for c in line) / max(len(line), 1) < .12:
                if line not in commentary:
                    commentary.append(line)
        warnings.extend(f"Page {page.number} note: {normalize(line)}" for line in page.notes)
    dates = {page.balance_as_of for page in pages if page.balance_as_of}
    return {"units": "INR crore", "periods": periods, "metrics": metrics,
            "balance": balance, "annualized_net_debt_to_ebitda": annualized, "segment_ebitda": segments, "sources": sources,
            "missing": missing, "warnings": warnings, "commentary": commentary,
            "page_count": len(pages), "balance_as_of": next(iter(dates)) if len(dates) == 1 else None}


def extract_pdf(data):
    pages, warnings = read_pdf(data)
    result = extract_pages(pages)
    result["warnings"] = warnings + result["warnings"]
    from .report_context import describe_report
    result["coverage"] = describe_report(pages, result["metrics"])
    # Do not populate unrelated company dashboards with Reliance's segment names.
    result["segment_ebitda"] = {key: pair for key, pair in result["segment_ebitda"].items()
                               if any(value is not None for value in pair.values())}
    result["missing"] = [key for key in result["missing"] if not key.startswith('segments.')
                         or key.rsplit('.', 1)[0][9:] in result["segment_ebitda"]]
    return result
