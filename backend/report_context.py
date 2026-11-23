"""Keep sourced narrative disclosures separate from extracted financial amounts."""
import re


def describe_report(pages, metrics):
    has_figures = any(value is not None for pair in metrics.values() for value in pair.values())
    cover = ' '.join(page.text for page in pages[:2])
    is_faq = bool(re.search(r'\bFAQ\b|frequently asked questions', cover, re.I))
    excerpts = []
    active = False
    section = []
    source_pages = set()
    for page in pages:
        for line in page.text.splitlines():
            line = re.sub(r'\s+', ' ', line).strip()
            if re.search(r'overview of Q[1-4].*results', line, re.I) and re.search(r'please|Q\d+\.', line, re.I):
                active = True
                continue
            if active and re.match(r'Q\d+\.', line):
                active = False
            if active and line and not line.isdigit():
                section.append(line)
                source_pages.add(page.number)
    # Verbatim sentences preserve net/gross, PBIT/EBITDA and adjustment distinctions.
    for sentence in re.split(r'(?<=[.!?])\s+', ' '.join(section)):
        if '%' in sentence and re.search(r'revenue|EBITDA|PAT|PBIT', sentence, re.I):
            excerpts.append({'text': sentence, 'pages': sorted(source_pages)})
    status = 'figures_available' if has_figures else 'narrative_only' if is_faq else 'no_supported_figures'
    reason = '' if has_figures else (
        'This FAQ provides narrative updates. No comparable quarterly financial amounts were extracted. '
        'Reported percentage changes are kept separate from amounts; ratios and financial health cannot be calculated. '
        'For a numerical dashboard, upload the quarterly financial results or investor presentation.'
        if is_faq else
        'No supported comparable financial table was extracted. The PDF may use an unsupported layout or image-based tables. '
        'Upload a financial results statement with selectable table text; this does not mean the company has no financial data.')
    return {'status': status, 'document_type': 'results_faq' if is_faq else 'financial_report',
            'reason': reason, 'reported_highlights': excerpts}
