@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo Virtual environment activated.
echo Starting SecureVision Flask server...
python app.py
pause
