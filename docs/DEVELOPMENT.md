# Development Guide

## Environment Setup

### 1. Requirements
- Node.js 20+ (Node 24 LTS verified)
- Python 3.11+
- uv (Python package installer)

### 2. Initial Setup
Run the setup script or manual commands:
```powershell
# Install Node workspace dependencies
npm install

# Setup Python virtual environment
uv venv backend/.venv
uv pip install -r backend/requirements.txt --python backend/.venv/Scripts/python.exe
```

## Running Tests

### Unit Tests
```powershell
# Run desktop React & Store vitest tests
npm test

# Run backend Pytest suite
backend\.venv\Scripts\python.exe -m pytest backend/tests
```

### Full Integration Smoke Test
Tests BaseWindow lifecycle, Chromium WebContentsView page loading, CDP observation, screenshot capture, Python process spawning, and JSON-RPC stdio roundtrips:
```powershell
# Build latest desktop bundle
npm run build:electron --workspace=@ai-browser/desktop
npx esbuild apps/desktop/tests/phase0-smoke.ts --outfile=apps/desktop/dist/tests/phase0-smoke.js --bundle --platform=node --target=node20 --format=cjs --external:electron

# Run test inside Electron
$env:ELECTRON_RUN_AS_NODE=$null; npx electron apps/desktop/dist/tests/phase0-smoke.js
```

## Running the Application

### Development Mode (with Hot Reload)
```powershell
npm run desktop:dev
```
This command starts:
1. Vite dev server for the React panels on `http://localhost:5173`.
2. Bundles the Electron main and preload scripts.
3. Launches Electron BaseWindow hosting Toolbar, Sidebar, Assistant panels, and active Chromium tab.
4. Electron automatically spawns the Python backend sidecar.
