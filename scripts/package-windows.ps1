# Package Windows NSIS Installer for AI Browser
Write-Host "Starting Windows Packaging Pipeline for AI Browser..." -ForegroundColor Cyan

# 1. Build Desktop Renderer
Write-Host "1/3 Building Vite React Frontend..." -ForegroundColor Yellow
npm run build:renderer --workspace=@ai-browser/desktop

# 2. Build Electron Main Process
Write-Host "2/3 Building Electron Main & Preload..." -ForegroundColor Yellow
npm run build:electron --workspace=@ai-browser/desktop

# 3. Run Electron-Builder
Write-Host "3/3 Generating NSIS Installer with electron-builder..." -ForegroundColor Yellow
npx electron-builder --win nsis --project apps/desktop

Write-Host "Windows Installer generated successfully in dist-installer/" -ForegroundColor Green
