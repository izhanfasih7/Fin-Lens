> Historical development notes. For the portable copy, use the root README.md, SETUP.md and VERIFICATION.md. Remote UI assets are now bundled locally.

# FinLens — deliverables 3–9

This project contains extraction, ratios, FastAPI, SQLite, FinBERT sentiment and
health classification. See [ML setup and model limitations](ml/README.md) for
deliverable 4. The [landing page](frontend/README.md) is deliverable 5 and is served
at http://127.0.0.1:8000/. Deliverable 6 adds the connected upload, results and history
pages. See [frontend behavior and verification](frontend/README.md).

- Home: http://127.0.0.1:8000/
- Upload: http://127.0.0.1:8000/upload
- Illustrative dashboard: http://127.0.0.1:8000/results/demo
- Saved analyses: http://127.0.0.1:8000/history

## Run (PowerShell, from this folder)

For a fresh computer, follow [SETUP.md](SETUP.md) for Python installation, model
preparation, startup and troubleshooting. On this already configured computer:

```powershell
.\.venv\Scripts\python.exe -X utf8 run.py
```

Or double-click `start.cmd`. Open http://127.0.0.1:8000/ to use the website.
Open http://127.0.0.1:8000/docs to try `POST /api/analyze` with a PDF directly.
`GET /api/history` lists saved uploads; `GET /api/analysis/{id}` retrieves one.
The server binds to localhost by default. Stop with Ctrl+C.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
curl.exe -F "file=@C:\path\to\your-report.pdf" http://127.0.0.1:8000/api/analyze
```

## Files

- `backend/extraction.py`: page discovery, table parsing, PyMuPDF text fallback,
  missing-value reporting, and page/row provenance.
- `backend/ratios.py`: pure ratio calculations, safe division and YoY growth.
- `backend/database.py`: parameterized SQLite queries; JSON result storage.
- `backend/main.py`: upload validation, API routes, background thread processing.
- `tests/test_backend.py`: synthetic extraction, ratio and API regression tests.
- `requirements.txt`: complete pinned dependencies, via `requirements-lock.txt`.
- `run.py` / `start.cmd`: local startup helpers.
- `SETUP.md`: fresh installation and troubleshooting instructions.

## Extraction contract

The JSON includes `periods`, `metrics`, `balance`, `segment_ebitda`, `ratios`,
`sources`, `missing`, `warnings`, `commentary`, `page_count` and upload metadata.
Financial amounts use INR crore. Ratio keys identify percent (`_pct`) or multiple
(`_x`). Metrics and segment EBITDA have `previous` and `current` fields.

Pages are discovered by consolidated, balance-sheet and segment-summary keywords.
Repeated segment financial-performance pages inherit the nearest detected section.
Column headers determine order; a single same-quarter consecutive-year period pair
is required. Mixed currency tables are accepted only when two period header cells
explicitly identify rupee-crore units. Ambiguous/multi-level headers are left null.
Table extraction has priority over text fallback; equally ranked conflicting values
are rejected. No amounts are inferred from surrounding prose or percentages.

Balance-sheet values require unambiguous single-value rows or a recovered table with
explicit date headers and rupee columns. For the latter, the latest date is selected
and returned as `balance_as_of`; ambiguous date layouts remain missing. The standalone balance
ratio is used when explicitly reported; otherwise net debt / LTM EBITDA is calculated.
ROE, ROA and current ratio are intentionally absent. YoY growth requires a positive
previous-year base. Commentary is classified with local FinBERT when installed.

## Validation and limitations

See [LIMITATIONS.md](LIMITATIONS.md) for the complete limitations, prioritized future
improvements and a project-report paragraph.

See [the testing guide](tests/README.md) for unit coverage and the opt-in real-PDF
checks. Missing sample checks are explicitly skipped, not claimed as passed.

The user's **76-page Q1 FY27 Reliance presentation** has now been checked against
pages 9–11: all 27 requested financial fields match the reviewed tables. Header-aligned
recovery supports its split currency/period headers and dated balance-sheet columns.
Its FY26 comparison excludes an investment gain, preserved in the dashboard notes.
The older **80-page Q1 FY26** sample from the initial brief is still unavailable;
its three checks remain skipped. Do not apply that older sample's ratio expectations
to the newer report. See [the FY27 regression](tests/test_ril_fy27.py).

The parser supports a conservative subset of quarterly presentation layouts, not
arbitrary annual reports. Wrapped labels, chart-only amounts, split currency headers,
scanned pages and unfamiliar aliases can yield nulls. OCR is not included. A PDF
with no selectable text returns HTTP 422. Corrupt/encrypted PDFs, non-PDF uploads,
files over 20 MB and reports over 200 pages are rejected. Some valid reports may
yield an analysis with all financial fields missing; inspect `warnings` and `missing`.

Upload processing is serialized per server process and runs outside the event loop.
This is a local project baseline, not a hardened public PDF-processing service.
SQLite defaults to `data/finlens.sqlite3`; set `FINLENS_DB` to change its location.
Uploaded PDF bytes are not retained; extracted text and values are retained in SQLite.
`requirements.txt` selects the exact versions verified in the local environment.

Deliverables 3–9 are documented. One actual FY27 Reliance report is validated for
the requested financial fields; broader report-layout validation remains future work.
