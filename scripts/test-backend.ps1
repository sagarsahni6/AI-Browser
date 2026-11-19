# Run Pytest suite for backend
Write-Host "Running Backend Pytest suite..." -ForegroundColor Cyan
& backend\.venv\Scripts\python.exe -m pytest backend/tests
