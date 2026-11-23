> Historical development notes. For the portable copy, use the root README.md, SETUP.md and VERIFICATION.md. Remote UI assets are now bundled locally.

# Deliverables 5 and 6: FinLens frontend

`index.html` contains all markup, CSS and JavaScript for the full-viewport hero.
FastAPI serves it at http://127.0.0.1:8000/. It uses no framework or build step.
Google Fonts provides Plus Jakarta Sans with `display=block`. Video and poster URLs
are preserved verbatim from the supplied specification; internet access is needed
for these assets. No images or videos have been downloaded into the project.

## Responsive measurements

Measured in headless Microsoft Edge with the loaded Plus Jakarta Sans font at
weight 500 and 100px size, using `CanvasRenderingContext2D.measureText`:

- `Financial reports,` advance width: **8.228 × font size**.
- Actual ink width: **8.059 × font size**, before letter spacing.
- The old spec's safety factor was `6.9 / 6.46`. Applying it gives
  `8.059 × 6.9 / 6.46 = 8.608`. The mobile divisor is **8.6**, with the specified
  negative letter spacing providing further room. Both lines use `white-space:nowrap`.
- Tablet width constraint changes from 575 to **750** reference units to accommodate
  the longer headline, while preserving the desktop 89u font size and offsets.
- Mobile CTA widths are approximately **144.14px + 135.14px + 10px gap = 289.28px**.
  With 40px side padding they fit from 330px upwards, so the stacking breakpoint is
  **329px**, replacing the original 353px.

Desktop measurements, typography, entrance timing and video framing follow the
supplied spec. At heights of 460px or less, a supplementary tablet/landscape rule
keeps the content below the navbar and makes the content area scrollable if needed;
the document itself retains `overflow:hidden`. The mobile menu also scrolls on
short viewports. This prevents essential actions becoming unreachable.

## Behavior

- Two videos cross-fade for 0.9 seconds at each loop boundary.
- The entrance waits for fonts (with the specified 900ms ceiling), then removes
  animation classes/listeners after the last CTA or a safety timeout.
- Reduced motion freezes the video at the first frame and skips entrance/transitions.
- The mobile menu opens/closes, dismisses on outside click or Escape, restores focus
  on Escape and closes when resizing back to desktop.
- Features, How It Works and Contact open keyboard-accessible native dialogs.
  These keep the requested single-screen composition without adding page sections.
- Docs opens the API documentation. `/upload` opens the connected upload form;
  `/results/demo` opens the illustrative dashboard.

## Verification

Browser checks cover desktop 1280×800 and 1920×1080; the 1160px nav boundary;
768px tablet; the 552px mobile boundary; 390px and 320px phones; CTA stacking;
short landscape; menu dismissal and focus; information dialogs; loaded video
metadata/playback; reduced motion. No reference screenshot was provided, so exact
pixel comparison against a reference image is not claimed.

## Deliverable 6: connected pages

- `upload.html` and `assets/upload.js`: PDF file picker, drag-and-drop, empty/file-size/
  extension validation, server errors and an elapsed-time processing state. Uploads
  go to `POST /api/analyze`. Successful responses navigate to `/results/{id}`.
  There is no simulated percentage progress. Duplicate submission is disabled while
  processing. The page warns before leaving an in-progress upload.
- `results.html` and `assets/results.js`: KPI cards, dynamic period comparisons,
  segment EBITDA, financial tables with source pages, ratio table, health score and
  scoring method, sentiment gauge and strongest sentences, factual summary, missing
  fields, warnings and JSON export. Saved results are loaded from `/api/analysis/{id}`.
- `history.html` and `assets/history.js`: empty/error/retry states, saved analyses,
  local-format timestamps, reopening reports and pagination in batches of 20.
- `assets/app.css`: shared black, violet and glass styling, Plus Jakarta Sans,
  pill buttons, responsive layouts and reduced-motion behavior.
- `assets/common.js`: number/date formatting, API error handling and safe DOM helpers.
- `backend/demo.py` and `GET /api/demo`: invented demo values, explicitly labelled
  on the page and in JSON. No real company is attributed and nothing is saved to SQLite.

Only results pages load Chart.js, pinned to 4.4.8 on jsDelivr. If that CDN is
unavailable, the underlying data tables remain accessible. Null values stay as dashes;
they are never converted into zero values or fabricated health/sentiment scores.
Pre-ML saved records also render with unavailable status rather than crashing.
Report filenames, warnings and commentary are inserted using `textContent`.

Run the existing FastAPI app from the project root, then visit `/upload` or
`/results/demo`. Refreshing a saved `/results/{id}` page works without localStorage.
The browser does not retain uploaded PDF bytes. The server saves extracted content
and analysis results in SQLite, as described in the root README.

### Completed checks

The 16 backend/ML tests pass, including page routes, static assets and a demo that
does not write history. Headless Edge checks verified desktop and mobile layouts
down to 320px, live Chart.js rendering, JSON export, invalid upload handling, missing
analysis pages, unavailable models, null values, safe text rendering and CDN failure.

An in-memory synthetic PDF also passed the full browser upload → actual PDF
extraction → FinBERT → saved results → history → reopening flow. That test ran on a
separate port/database so it did not create fictitious reports in the user's history.
Subsequently, the user's real 76-page FY27 Reliance PDF was validated against its
tables on pages 9–11. Its dashboard includes comparison-basis footnotes and the
balance-sheet date. The original older 80-page FY26 sample remains unavailable.
