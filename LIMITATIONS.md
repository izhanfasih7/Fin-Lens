> Historical development notes. For the portable copy, use the root README.md, SETUP.md and VERIFICATION.md. Remote UI assets are now bundled locally.

# FinLens: limitations and future improvements

FinLens demonstrates a complete local workflow: upload a PDF, extract supported
financial figures, calculate ratios, classify commentary, display an educational
health rating, and save the analysis. It is a final-year engineering prototype.
Its main research limitation is the absence of independent validation on real
reports and independently labelled financial-health outcomes.

## Current limitations

### 1. PDF coverage is narrow

The extractor uses page keywords, row-label patterns, period headers and nearby
segment context. It is designed around quarterly-presentation conventions. It does
not support arbitrary annual reports despite the broader wording on the landing page.
Different titles, wrapped labels, merged cells, multi-level headers or multi-date
balance tables can leave values missing. Nearby section context can also be
misidentified; a non-null result is not proof of correct extraction.

Selectable text is required. There is no OCR or extraction from chart graphics.
Password-protected, corrupt and text-free PDFs are rejected. Uploads are limited
to 20 MB and 200 pages. Ambiguous currency columns, competing period pairs and
equally ranked conflicting values are left null. Page references and missing-field
lists assist review, but no extraction-confidence estimate is currently available.

**The original 80-page Reliance Q1 FY26 PDF has not been supplied.** Its three tests
remain skipped. A different, 76-page Q1 FY27 report from the user's Desktop has now
been validated: all 27 requested financial fields match visually reviewed tables
on pages 9–11. This establishes coverage for that report, not arbitrary layouts.

### 2. Ratio correctness depends on the inputs

The ratio functions are deterministic and tested, but a correctly calculated ratio
can still be misleading if the extracted amount or period is wrong. The application
does not automatically reconcile the income statement, identify restatements,
separate exceptional items, or confirm accounting definitions across companies.

Only supported ratios are calculated. ROE, ROA and current ratio are omitted. YoY
growth is omitted for missing or non-positive prior-year bases. Interest coverage
uses EBITDA divided by finance cost, as specified for this project. Net debt uses
reported net debt/LTM EBITDA when found, otherwise the two extracted amounts.
These definitions should be disclosed when comparing results with other sources.

### 3. The health classifier learns project rules

The public dataset did not contain verified Good/Average/Risky labels. Preparation
creates labels from thresholds applied to five ratios. The Random Forest therefore
learns to reproduce those rules; it has not learned independently established
financial health or future bankruptcy outcomes.

The completed run used **141 rows from 12 companies**, split into 109 training and
32 test rows with companies separated between sets. Test accuracy was **84.375%**
and macro F1 **0.7283**. These measure agreement with the generated labels.
Only two test examples were labelled Risky, and the model identified one of them.
A single small split provides limited evidence of generalization.

Training data consists of annual US company observations, while the intended sample
is an Indian quarterly presentation. Sector, accounting and reporting-period
differences are not modelled. Finance cost and debt are not included in the five
model features. No probability calibration or out-of-distribution detection is used.

The displayed score is `100 × P(Good) + 50 × P(Average)` and the rating is the most
probable class. It is not a probability of financial safety or default. With fewer
than four available ratios, the model is bypassed; ratio rules are used when at
least two ratios exist. With less data, no rating is assigned. A rating based on
two ratios has less evidence than one based on five, even if both display Good.

### 4. Sentiment describes language, not financial truth

FinBERT is used pretrained, without project-specific fine-tuning or a labelled
evaluation set of management commentary. Three sample sentences verified that
inference runs; they do not establish sentiment accuracy.

Commentary selection is based on line length and digit density. Short slide titles
may be excluded, wrapped bullets may become incomplete statements, and narrative
table text may be included. The application analyzes the first 240 unique eligible
sentences, so later commentary can be underrepresented. Inputs longer than 512
tokens are truncated. Counts of skipped and truncated sentences are displayed.

English-language use is assumed. Promotional wording, negation, mixed statements,
technical terminology and context across slides can affect classification. The
sentiment gauge summarizes model probabilities; it does not verify the company's
claims or independently confirm its financial condition.

### 5. Runtime and deployment are designed for local use

Uploads are serialized within each server process. FinBERT runs on CPU, and the
first analysis can be slower because weights must be loaded. There is no durable
job queue, processing-stage progress, cancellation, or resumable background task.
If a connection drops, the analysis may still finish; History should be checked
before uploading again.

There is no login or separation between users' records, consistent with the project
scope. SQLite is suitable for this local demonstration; public multi-user operation
would require further design. File-size and page-count checks do not provide
process isolation or comprehensive resource controls for untrusted PDFs.

Uploaded PDFs are not retained, but extracted text and analyses are saved in the
local SQLite database. There is no in-app deletion, retention policy or automatic
backup. Without the original PDF, saved page references cannot reopen its contents.

Analysis runs locally after model setup. Fonts, the hero video/poster and Chart.js
still depend on remote hosts. Offline charts fall back to data tables; complete
offline visual behavior is not guaranteed. Setup has been verified on Windows x64
with Python 3.12, not on a clean installation of every supported Python/platform
combination. Browser checks used Microsoft Edge; broad browser and assistive-
technology testing remains outstanding.

## Prioritized future improvements

These are proposed extensions, not features already implemented.

| Priority | Improvement | How to verify it |
| --- | --- | --- |
| 1 | Validate the actual Reliance PDF and build a manually checked table of expected amounts, units, periods, segments and page numbers. | Run the optional checks and compare every extracted field, including wrong values and missed fields. |
| 2 | Build a varied report benchmark before expanding label patterns and table parsing. Include unfamiliar layouts and negative examples. | Report field-level precision, recall, amount accuracy and period/unit errors on reports held out from parser development. |
| 3 | Add layout-aware extraction, explicit segment boundaries, multi-level currency/date headers and accounting reconciliation warnings. | Test ambiguous cases and confirm that unsupported layouts remain missing rather than silently misassigned. |
| 4 | Add OCR for scanned pages while preserving page coordinates and reviewable source snippets. | Measure OCR/extraction errors separately on scanned reports, especially commas, minus signs and decimals. |
| 5 | Replace rule-derived health labels with independently reviewed labels or clearly defined future outcomes; expand Indian quarterly and sector coverage. | Use company-separated and time-separated evaluation, compare with the rule baseline, report per-class metrics and uncertainty, and check calibration. |
| 6 | Improve commentary reconstruction and create a human-labelled sentiment test set. Consider section-balanced sampling and long-text handling. | Measure per-class precision/recall and inspect errors on negation, mixed sentiment and promotional language. |
| 7 | Add asynchronous jobs with status, cancellation, bounded resources and duplicate-upload detection. | Verify recovery after connection loss, repeated uploads and server restarts; measure latency and memory on representative reports. |
| 8 | Add review/correction workflows, explicit provenance and model-version metadata, optional report retention and history deletion/export. | Confirm corrected values remain traceable, saved results can be reproduced, and deletion removes the intended records only. |
| 9 | Improve accessibility, cross-browser coverage and optional offline assets. | Test keyboard and screen-reader use, mobile browsers, reduced motion and loss of each remote asset. Keep the currently specified hero URLs unless the design requirement changes. |

Public hosting, authentication and a shared database are optional later extensions.
They are not required for the current no-login local project.

## What the present evidence supports

- **Software regression checks:** with the FY27 report enabled, 54 tests pass;
  3 older FY26 report tests are skipped.
  The suite covers calculations, extraction edge cases, PDF-reader failures, API
  persistence and ML handling. This is not a percentage estimate of extraction accuracy.
- **Workflow checks:** a synthetic PDF passed browser upload, actual extraction,
  FinBERT inference, dashboard rendering, SQLite storage and reopening from History.
- **Model experiment:** the saved health-model metrics quantify agreement with
  generated ratio-rule labels on a small held-out set of companies.
- **Real-report extraction:** the FY27 Reliance tables on pages 9–11 were visually
  checked and covered by a full-PDF regression plus offline layout fixtures.
- **Unverified:** the original FY26 sample, extraction across arbitrary annual
  reports, independent financial-health prediction and real-report sentiment accuracy.

See the [testing guide](tests/README.md), [saved model metrics](models/health.metrics.json),
[ML methodology](ml/README.md) and [setup guide](SETUP.md) for the underlying details.

## Paragraph for the project report

FinLens demonstrates the integration of PDF extraction, financial ratio calculation,
financial-text sentiment analysis and an interactive dashboard. Its current
limitations include dependence on supported PDF layouts, lack of OCR, approximate
commentary extraction and a small health-classification dataset with labels derived
from predefined ratio rules. Consequently, classifier accuracy represents agreement
with those rules rather than independently validated financial-health prediction.
The application has passed automated regression tests and a synthetic end-to-end
workflow test. The requested financial fields were also verified against one real
FY27 Reliance presentation; the older FY26 sample remains unavailable. Future work
should prioritize a wider collection of manually verified report benchmarks,
layout-aware extraction, independently labelled health data, domain-specific
sentiment evaluation and improved processing reliability.

Results FAQs without extracted comparable amounts now show sourced narrative highlights separately. This does not provide general extraction coverage for every company, annual period, currency, or image-based table. Unrelated Reliance segment placeholders are omitted. Existing saved analyses require reanalysis to receive coverage metadata.

Consolidated earnings-release highlights with split nQ/FY headers are now supported and checked against reliance 26.pdf and reliance 28.pdf. The parser selects the latest quarter and matching prior-year quarter, excluding intervening-quarter, YTD, and annual columns. Combined PAT including associates/JVs is preferred and disclosed. Reported annualised debt/EBITDA is separate from LTM leverage. Segment and statutory date-header tables in these releases remain unsupported; LTM values are not inferred.

When no financial amounts can be extracted, scanned PDFs and unsupported layouts now receive a labelled illustrative dashboard. Sample data is kept separate from the extracted report, preserved in exported JSON. Partial real extractions are never filled with sample values. Corrupt/password-protected PDFs, oversized files, storage failures and connectivity problems can still prevent analysis; universal error-free processing is not guaranteed.

Validation update (13 October 2026): the dated statutory consolidated segment EBITDA tables in reliance 26.pdf and reliance 28.pdf are now supported, with explicit Quarter Ended group selection and separation from EBIT, YTD, annual and standalone data. Segment EBITDA excludes unallocated group items, so it need not sum to consolidated EBITDA. Results FAQs containing sourced overview excerpts now show real commentary instead of an automatic synthetic fallback. This is parser validation, not model training or a guarantee for all PDF layouts.
