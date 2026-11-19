# Build packaged Python backend for Windows distribution
Write-Host "Packaging Python Backend for Windows..." -ForegroundColor Cyan

$backendDir = Join-Path $PSScriptRoot "..\backend"
Set-Location $backendDir

# Ensure pyinstaller is installed in virtual environment
Write-Host "Ensuring PyInstaller is installed..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe -m pip install pyinstaller

Write-Host "Compiling standalone backend executable with PyInstaller..." -ForegroundColor Yellow
& .\.venv\Scripts\pyinstaller.exe `
    --onefile `
    --name ai_browser_backend `
    --distpath (Join-Path $PSScriptRoot "..\apps\desktop\resources\backend") `
    --workpath (Join-Path $backendDir "build") `
    --specpath (Join-Path $backendDir "build") `
    --clean `
    app/main.py

Write-Host "Backend packaging complete!" -ForegroundColor Green
