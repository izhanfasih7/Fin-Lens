> Submission note: current validation is recorded in ../VERIFICATION.md. Counts below describe earlier development stages.

# Deliverable 8: ratio and extraction tests

Run from the project root, after installing the complete `requirements.txt`:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
```

No model downloads or network access are needed for the unit suite. The installed
scikit-learn packages are needed for the model training round-trip tests. The API
test uses a temporary database; it does not write to your saved analysis history.

With the user's FY27 PDF enabled, the expanded suite has **57 tests: 54 pass and
3 older FY26 sample checks skip**. Without either PDF environment variable, 53 pass
and 4 skip. The Starlette/httpx deprecation notice is not a failed test.

## Validated FY27 report

`test_ril_fy27.py` checks all financial amounts on the user's 76-page
`Presentation_for_RIL_Analyst_Meeting_v17072026.pdf`. Expected values were visually
reviewed on pages 9 (consolidated results), 10 (segment EBITDA), and 11 (balance sheet).
The versioned word-position fixture records the source SHA-256 and supports offline
regressions for split headers, wrapped labels, rupee/USD separation and date selection.
It also checks that moving the table does not change its extracted values.

```powershell
$env:FINLENS_FY27_PDF = 'C:\Reports\Presentation_for_RIL_Analyst_Meeting_v17072026.pdf'
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
```

This report compares Q1 FY26 against Q1 FY27. Current PAT margin is 6.82% and
interest coverage is 6.49×. These differ from the original older-report expectations
below. Comparison footnotes are retained; FY26 excludes profit on listed investments.

## Test layers

| File | What it verifies |
| --- | --- |
| `test_ratios.py` | All supported margins, tax rate, coverage and growth; missing/zero denominators; non-positive growth bases; losses; reported versus computed leverage; zero/negative debt; input preservation. |
| `test_extraction_edges.py` | Indian number formatting, footnotes, missing values, keyword-based page discovery, explicit rupee columns alongside USD, period ambiguity, table priority, segment context, segment revenue versus EBITDA, balance-date ambiguity and source consistency. |
| `test_pdf_reader.py` | Actual parsing of an in-memory synthetic PDF; fallback when pdfplumber fails; corrupt, encrypted, text-free and over-200-page reports. No PDF fixture files are saved. |
| `test_backend.py` | Original numerical fixtures, conflicts, API errors, page/static routes, demo isolation and SQLite save/retrieve. |
| `test_ml.py` | Missing-data fallback, company-separated training split, model export/reload, sentence splitting, sentiment aggregation and unavailable-model states. |
| `test_reliance_sample.py` | Opt-in checks on the actual 80-slide Reliance presentation. These are skipped by default, not reported as passed. |

The numerical examples are deliberately synthetic. The first fixture was chosen to
produce 11.3% and 6.8% PAT margins, and 8.2× and 7.2× interest coverage. This tests
arithmetic, not whether these figures can be extracted correctly from Reliance's PDF.
New independent examples exercise different margins and growth rates.

## Run against the real Reliance sample

The original 80-page FY26 file has not been supplied. When it is available, set its real absolute
path in PowerShell and run the optional module:

```powershell
$env:FINLENS_SAMPLE_PDF = 'C:\Reports\Reliance-Q1-FY26.pdf'
.\.venv\Scripts\python.exe -X utf8 -m unittest tests.test_reliance_sample -v
```

That path is an example; point it to your actual file. Once the variable is set,
missing files, parsing failures and mismatched values fail rather than skip.
The checks require:

1. The specified 80 pages and Q1 FY25 / Q1 FY26 period pair.
2. PAT margin of 6.8% / 11.3% and interest coverage of 7.2× / 8.2×, allowing 0.05
   absolute difference to accommodate the supplied one-decimal expectations.
3. All requested income-statement, balance and segment figures, with source entries;
   income-statement source page numbers must fall within the PDF.

These checks do not establish correctness of every raw amount: the prompt did not
supply a complete table of expected values. Manually compare extracted figures and
source pages with the actual report before calling the extractor validated. If you
use a different report edition, review its expected page count and figures first.

To remove the optional sample setting afterward:

```powershell
Remove-Item Env:FINLENS_SAMPLE_PDF
```

For just the portable ratio/extraction/reader tests:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest tests.test_ratios tests.test_extraction_edges tests.test_pdf_reader -v
```

## Regression fixed in this delivery

The expanded numeric-format test exposed `normalize(0)` returning an empty string.
Normalization now distinguishes `None` from numeric zero, so zero remains a known
value. The parser also uses the current `pymupdf` import name rather than the
deprecated `fitz` import alias. Both are exercised by the real-parser tests.
