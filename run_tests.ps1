$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir
& ".\venv\Scripts\Activate.ps1"
Write-Host "Virtual environment activated." -ForegroundColor Green
Write-Host "Running SecureVision test suite..." -ForegroundColor Cyan
python -m pytest tests/ -v
