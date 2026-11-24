@echo off
cd /d "%~dp0"
if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv
  .venv\Scripts\python.exe -m pip install -q -r requirements.txt
)
start "" http://127.0.0.1:8170
.venv\Scripts\python.exe run.py
