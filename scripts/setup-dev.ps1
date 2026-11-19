# Setup development environment for AI Browser
Write-Host "Setting up AI Browser monorepo..." -ForegroundColor Cyan

# 1. NPM Install
Write-Host "Installing npm dependencies..." -ForegroundColor Yellow
npm install

# 2. Python Virtual Environment
Write-Host "Configuring Python virtual environment in backend/.venv..." -ForegroundColor Yellow
if (-not (Test-Path "backend/.venv")) {
    uv venv backend/.venv
}
uv pip install -r backend/requirements.txt --python backend/.venv/Scripts/python.exe

Write-Host "Setup complete! You can now run 'npm run desktop:dev'." -ForegroundColor Green
