@echo off
cd /d %~dp0
echo Checking dependencies (first run may take a minute)...
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo Could not install dependencies. Make sure Python 3.9+ is installed and on PATH.
    pause
    exit /b 1
)
echo Starting StellaAudits...
python app.py
pause
