# Verification — 13 October 2026

## Completed on this Windows machine
- Copied source into an independent Project-Submission directory; original backend/frontend files and running site were not modified.
- Copied-project unittest run using the existing full Python environment: 70 tests, 66 passed, 4 optional full-PDF tests skipped.
- Created a NEW isolated Python 3.12 virtual environment outside the deliverable. Installed requirements-backend.txt successfully and ran pip check successfully.
- In that new backend-only environment, verified HTTP routes, all 17 bundled asset files, a generated selectable-text PDF upload, labelled fallback, SQLite initialization, history and JSON retrieval. Database used a temporary directory and is not bundled.
- Full pinned requirements: existing-environment pip check and offline dry-run passed. This is NOT a fresh installation of the full ML stack.
- Original backend and ML source files were preserved byte-for-byte. Frontend changes only localize remote asset URLs and replace email/phone with approved placeholders.
- No original .git metadata, virtual environments, databases, logs, full PDFs, user reports, training CSVs or FinBERT weights were copied.
- Hidden .gitignore and .env.example are included. No required API credentials. Optional variables are documented and are NOT loaded from .env automatically.

## Not verified / external requirements
- No test on another physical computer, macOS or Linux; no claim of universal clean-machine compatibility.
- Full ML dependency installation, FinBERT download and model inference were not repeated in the fresh environment. The included classifier originated from the working installation; it may require compatible scikit-learn versions.
- Package installation and optional model/training-data downloads need internet. The downloadable model is public but availability is controlled by its provider.
- The hero media's redistribution license was not independently established. Sources and hashes are in ASSET-MANIFEST.json; review THIRD_PARTY.md before public distribution.
- No deployment or GitHub upload has been performed. This is a clean source package, not a hosted website or an installer.
- Secret-pattern and excluded-file checks are safeguards, not a guarantee against every conceivable sensitive string. Review intended public profile content before publication.
