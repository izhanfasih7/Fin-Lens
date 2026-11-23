> Historical development notes. For the portable copy, use the root README.md, SETUP.md and VERIFICATION.md. Remote UI assets are now bundled locally.

# FinLens setup and run guide

This guide covers deliverable 7. The application has no login, Docker, Node.js
installation or frontend build step. The verified environment is **Windows x64,
Python 3.12**. `requirements.txt` includes the exact package versions recorded in
`requirements-lock.txt`, including the backend, ML and test dependencies.

## Already set up on this computer

The `.venv` environment and both models have already been installed in this folder.
The local server may already be running: open [FinLens](http://127.0.0.1:8000/).
If it is reachable, there is no need to start another instance.

For later launches, double-click **start.cmd** and keep its terminal open. Or open
PowerShell in this folder and run:

```powershell
.\.venv\Scripts\python.exe -X utf8 run.py
```

Wait for Uvicorn's “Application startup complete” message, then open
[http://127.0.0.1:8000/](http://127.0.0.1:8000/). Stop with **Ctrl+C** in the server
terminal. Closing that terminal also stops a normally launched server.

## Fresh installation on another Windows computer

Install Python 3.12 x64 with the Python launcher, then open PowerShell in the
project folder. Keep the source folder structure intact, including `frontend/assets`.
Do not copy `.venv` from another computer: recreate it with the commands below.
Allow several GB of disk space for packages, model weights and the download cache.

### 1. Create the environment and install packages

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -X utf8 -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -X utf8 -m pip check
```

These commands use the environment's Python directly, so there is no activation
script or PowerShell execution-policy change. If `py` is unavailable but `python
--version` reports Python 3.12, use `python -m venv .venv` instead.

### 2. Prepare the health model

```powershell
.\.venv\Scripts\python.exe -X utf8 -m ml.prepare_data
.\.venv\Scripts\python.exe -X utf8 -m ml.train_health
```

The first command downloads the public dataset and writes
`data/training/company_ratios.csv`. The second trains the classifier, exports
`models/health.joblib` and writes accuracy, F1 and the confusion matrix to
`models/health.metrics.json`. The labels are derived from ratio rules; see
[the ML guide](ml/README.md) before describing its accuracy in your report.

If Kaggle's direct download is unavailable, download the CSV from the dataset link
in the ML guide and supply its actual path:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m ml.prepare_data --raw-csv "C:\Reports\Financial Statements.csv"
.\.venv\Scripts\python.exe -X utf8 -m ml.train_health
```

### 3. Download FinBERT once

```powershell
.\.venv\Scripts\python.exe -X utf8 -m ml.download_finbert
```

This downloads pretrained weights from Hugging Face and saves the model in
`models/finbert`. The weights alone are about 438 MB; the Hugging Face cache can
retain another copy. No GPU is required. Subsequent analysis loads these local
weights; the first analysis after starting the server may take longer.

### 4. Run the checks and start the app

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 run.py
```

Open the home page and choose **Get Started** to upload a report, or **See Demo** to
explore invented example figures. An upload supports one selectable-text PDF,
20 MB or smaller, up to 200 pages. Follow the processing state until results appear.

| Page | Local address |
| --- | --- |
| Home | http://127.0.0.1:8000/ |
| Upload | http://127.0.0.1:8000/upload |
| Illustrative demo | http://127.0.0.1:8000/results/demo |
| Saved history | http://127.0.0.1:8000/history |
| Interactive API | http://127.0.0.1:8000/docs |

## Everyday use and development

The model setup commands are one-time steps. For everyday use, just start the app.
To watch source-code edits automatically, run:

```powershell
.\.venv\Scripts\python.exe -X utf8 run.py --reload
```

To use another port without disrupting an existing server:

```powershell
.\.venv\Scripts\python.exe -X utf8 run.py --port 8002
```

Then visit http://127.0.0.1:8002/. `run.py` resolves the project directory and its
virtual environment even if it is launched by absolute path from another folder.
It binds only to `127.0.0.1`; other devices cannot use this loopback address to
connect to your computer.

## Files, data and configuration

- `requirements.txt`: the recommended complete installation entry point.
- `requirements-lock.txt`: exact versions from the tested environment; keep it with
  `requirements.txt` when sharing the source. It is a version snapshot, not a
  cross-platform or cryptographic package lock.
- `requirements-backend.txt`: optional lightweight installation without ML packages.
- `requirements-ml.txt`: the earlier full installation with version ranges. Use the
  pinned `requirements.txt` for reproducing this delivery.
- `data/finlens.sqlite3`: extracted report text and saved analyses. Uploaded PDFs
  themselves are not stored. Copy this database while the server is stopped to back
  up your history; its content may include confidential report text.
- `models/health.joblib`, `models/finbert/`: trained classifier and cached FinBERT.
  These and `data/` are ignored by Git; a source checkout needs the setup steps.

Optional variables must be set in the same terminal **before** starting the server:

```powershell
$env:FINLENS_DB = 'C:\FinLensData\finlens.sqlite3'
.\.venv\Scripts\python.exe -X utf8 run.py
```

`FINLENS_HEALTH_MODEL` overrides the classifier path. `FINLENS_FINBERT_DIR` overrides
the local FinBERT directory. Use absolute paths for these overrides. Restart after
changing settings or replacing FinBERT weights. Only load joblib models you trust.

Without a health model the API uses labelled ratio rules where enough ratios are
available. Without FinBERT it reports sentiment as unavailable, not neutral. The full
test suite requires the ML packages even if you choose a backend-only installation.

Internet access is needed for initial package/data/model downloads. Report analysis
runs locally afterward. The UI still requests Google Fonts, the landing-page video
and poster, and Chart.js on results pages. Without those remote assets the video
may be blank, fonts fall back, and charts fall back to the accessible data tables.

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| “Website can't be reached” | Start the server and wait for startup completion. Keep its terminal open and use the port printed there. |
| Port 8000 is already in use / WinError 10048 | Try the existing home page first. Stop the old server with Ctrl+C in its own terminal, or run on port 8002. |
| `py` or `python` is not recognized | Install Python 3.12 x64, then open a new terminal. |
| `ModuleNotFoundError` | Install `requirements.txt` using `.venv\Scripts\python.exe`; avoid a different global Python. |
| pip console encoding errors | Use the documented `-X utf8` commands, especially when the project path contains non-Latin text. |
| FinBERT unavailable | Run `ml.download_finbert`, confirm `models/finbert` exists, and restart. Read the server traceback if loading still fails. |
| Training/model version error | Install the pinned requirements, then rerun preparation and training in that environment. |
| HTTP 413 / 415 / 422 | Respectively: reduce file size; choose a real PDF; inspect the message for corruption, encryption, page count or missing selectable text. |
| Many missing figures | The table layout or labels may be unsupported. Compare the source PDF with the missing-field list. No values are guessed. |
| Long processing time | FinBERT runs on CPU and uploads are processed serially. Keep the page open; inspect the server terminal for errors. |
| Connection lost after upload | Check History before uploading again; the server may have completed and saved the analysis. |
| Charts unavailable | Check access to jsDelivr, or open the financial/segment tables beneath each chart. |

The original server started by this chat logs to `data/server.log` and
`data/server-error.log`. The normal launcher prints directly to its terminal.

## Verification limits

The existing environment passes the automated suite and the browser upload-to-history
check with a synthetic PDF. The pinned install was checked against the existing
environment with an offline dry run, and `pip check` found no broken requirements.
The launcher was verified from outside the project folder on a separate port.
A fresh install on another operating system has not been
verified. The user's 76-page FY27 Reliance PDF has since been checked against pages
9–11 with all 27 requested fields recovered. The original 80-page FY26 sample is
still unavailable; see the testing guide for the separate report-specific checks.
