# Setup
Follow the current installation instructions in [README.md](README.md). Start with Python 3.12 and create a new `.venv`; never copy an environment from another computer. No environment, history database, or FinBERT download is bundled. The small health classifier is included.

Default URL: http://127.0.0.1:8000/. Run `python run.py --port 8001` for a different port. Keep the process running. On Windows, `start.cmd` uses the project's virtual environment after installation.

If installation fails, check network access, Python version and wheel availability. The full lock was captured on Windows x64. A compatible-ranges alternative is `requirements-ml.txt`. Missing FinBERT does not stop the site: run `python -m ml.download_finbert` to enable sentiment, then restart.

Static fonts, video, poster and Chart.js are bundled locally. Profile links open external websites. Report processing and SQLite operate locally. For precise verification limitations see [VERIFICATION.md](VERIFICATION.md).
