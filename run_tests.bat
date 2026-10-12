@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo Virtual environment activated.
echo Running SecureVision test suite...
python -m pytest tests/ -v
pause
