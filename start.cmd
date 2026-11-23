@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo FinLens needs its local environment. Follow SETUP.md first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -X utf8 "run.py" %*
if errorlevel 1 (
  echo.
  echo FinLens could not start. Read the error above and SETUP.md.
  pause
  exit /b 1
)
