# Build Desktop Application
Write-Host "Building Desktop Renderer (Vite)..." -ForegroundColor Cyan
npm run build:renderer --workspace=@ai-browser/desktop

Write-Host "Building Electron Main & Preload (esbuild)..." -ForegroundColor Cyan
npm run build:electron --workspace=@ai-browser/desktop

Write-Host "Desktop build completed successfully." -ForegroundColor Green
