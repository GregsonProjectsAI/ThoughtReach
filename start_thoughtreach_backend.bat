@echo off
if not exist "venv\Scripts\python.exe" (
    echo Error: venv\Scripts\python.exe not found. Please ensure the virtual environment is set up.
    pause
    exit /b 1
)

echo Starting ThoughtReach Backend...
venv\Scripts\python.exe -m uvicorn app.main:app --reload
pause
