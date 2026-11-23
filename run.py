"""Start FinLens from any working directory, using this project's virtual environment."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="Start the local FinLens website.")
    parser.add_argument("--port", type=int, default=8000, help="Local port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Restart automatically after code edits")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")

    venv_python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not venv_python.is_file():
        print("FinLens needs its local environment. Follow SETUP.md first.", file=sys.stderr)
        return 1
    if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
        return subprocess.call([str(venv_python), "-X", "utf8", str(Path(__file__).resolve()), *sys.argv[1:]])

    # Keep SQLite and the application import path stable when launched elsewhere.
    os.chdir(ROOT)
    try:
        import uvicorn
    except ImportError:
        print("Install dependencies first: .venv/Scripts/python.exe -m pip install -r requirements.txt",
              file=sys.stderr)
        return 1
    print(f"Starting FinLens at http://127.0.0.1:{args.port}/", flush=True)
    print("Keep this terminal open. Press Ctrl+C to stop.", flush=True)
    uvicorn.run("backend.main:app", host="127.0.0.1", port=args.port, reload=args.reload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
