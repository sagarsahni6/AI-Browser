# AI Browser

A production-grade, AI-powered autonomous desktop browser inspired by the user experience of Perplexity Comet. Combines full Chromium browsing with an integrated AI intelligence system capable of understanding webpages, conducting cited research, controlling the browser, and completing multi-step autonomous tasks.

## Key Features

- **Chromium Browsing Engine**: Multi-tab browsing powered by Electron's modern `BaseWindow` and `WebContentsView` architecture.
- **Deep Webpage Understanding**: Real-time DOM inspection, accessibility tree extraction, and vision capture through an internal, controlled Chromium DevTools Protocol (CDP) bridge.
- **Local AI Agent Orchestration**: Python FastAPI sidecar running bidirectional JSON-RPC 2.0 over standard streams (`stdin`/`stdout`), keeping remote debugging ports closed.
- **Multi-Provider AI Architecture**: NVIDIA NIM as primary provider (supporting Llama-3.3-70b-instruct and Llama-3.2-90b-vision-instruct) with OpenAI-compatible fallback.
- **Strict Local Security**: No remote debugging port exposed to the network, no Node.js integration inside web content, OS-level secure storage for API credentials, and cryptographically generated per-session IPC authentication.

## Project Structure

```
ai-browser/
├── apps/
│   └── desktop/               # Electron BaseWindow shell + React / Vite frontend
│       ├── electron/          # Main process TypeScript controllers
│       ├── src/               # React UI panels (Toolbar, Sidebar, Assistant)
│       └── tests/             # Vitest unit tests & Phase 0 smoke test
├── backend/                   # Python FastAPI service & agent orchestration
│   ├── app/                   # FastAPI routes, browser bridge, agents, AI router
│   └── tests/                 # Pytest unit tests (health, JSON-RPC protocol)
├── shared/                    # Shared TypeScript contracts, IPC channels, and RPC types
├── scripts/                   # Development, build, and packaging PowerShell scripts
└── docs/                      # Architecture, Security, API, and Development guides
```

## Getting Started

### Prerequisites

- **Node.js**: v20+ (Node v24 recommended)
- **Python**: 3.11+
- **uv**: Fast Python package manager (recommended) or pip

### Quick Start

1. **Install JavaScript dependencies**:
   ```powershell
   npm install
   ```

2. **Setup Python environment**:
   ```powershell
   uv venv backend/.venv
   uv pip install -r backend/requirements.txt --python backend/.venv/Scripts/python.exe
   ```

3. **Run tests**:
   ```powershell
   # Desktop frontend tests
   npm test

   # Backend Python tests
   backend\.venv\Scripts\python.exe -m pytest backend/tests

   # End-to-end Phase 0 integration smoke test
   $env:ELECTRON_RUN_AS_NODE=$null; npx electron apps/desktop/dist/tests/phase0-smoke.js
   ```

4. **Launch development environment**:
   ```powershell
   npm run desktop:dev
   ```

## Documentation

- [Architecture Guide](docs/ARCHITECTURE.md)
- [Security Specifications](docs/SECURITY.md)
- [API Reference](docs/API.md)
- [Development Workflow](docs/DEVELOPMENT.md)
