# System Architecture

## Overview

AI Browser is built around a five-layer decoupled desktop architecture:

```
┌────────────────────────────────────────────────────────┐
│                   Electron BaseWindow                  │
├────────────────────┬──────────────────┬────────────────┤
│  Toolbar Panel     │  Navigation      │  AI Assistant  │
│  (WebContentsView) │  Sidebar         │  Sidebar       │
│                    │ (WebContentsView)│(WebContentsView│
├────────────────────┴──────────────────┴────────────────┤
│            Active Tab (WebContentsView)                │
│       Isolated Chromium remote webpage context         │
└────────────────────────────────────────────────────────┘
                           │
                 Controlled CDP Bridge
                           │
┌──────────────────────────▼─────────────────────────────┐
│                 Electron Main Process                  │
│       LayoutManager, TabManager, DebuggerManager       │
│       ProcessManager, RpcClient, SecurityGuard         │
└──────────────────────────┬─────────────────────────────┘
                           │
        Bidirectional JSON-RPC 2.0 (stdio)
                           │
┌──────────────────────────▼─────────────────────────────┐
│               Python FastAPI Backend                   │
│        BrowserBridge, Agent Supervisor, AI Router      │
│        NVIDIA NIM Provider, SQLite Local Memory        │
└────────────────────────────────────────────────────────┘
```

## Layer Specifications

### 1. Desktop Browser Shell
- Built with Electron `BaseWindow` and independent `WebContentsView` instances.
- UI panels (`Toolbar`, `Sidebar`, `Assistant`) load the trusted local React application with panel routing (`?panel=toolbar`, etc.).
- Centralized `LayoutManager` recalculates panel bounds on window resize and panel collapse/expand events.
- Background tabs remain active without destroying Chromium state; inactive tab views are assigned zero bounds to prevent visual occlusion or click interception.

### 2. Browser Control Engine & CDP Bridge
- Uses Electron's built-in `webContents.debugger` API.
- Attaches to Chromium DevTools Protocol (CDP) internally (protocol version 1.3).
- No external network debugging port (`--remote-debugging-port`) is ever exposed.
- Provides structured observations:
  - Bounding boxes and accessibility metadata of interactive elements (`a`, `button`, `input`, etc.).
  - Visible text extraction without sensitive credential fields.
  - Page screenshot capture with base64 PNG export.

### 3. Electron-Python IPC & RPC Bridge
- Process lifecycle is owned by Electron's `ProcessManager`.
- Spawns the Python backend as a child process with a cryptographically generated 256-bit authentication token passed via protected environment variables.
- Communication uses JSON Lines over standard streams (`stdin` / `stdout`).
  - `stdout` is strictly reserved for protocol messages.
  - `stderr` is reserved for diagnostic logs.
- Bidirectional JSON-RPC 2.0 allows Python agents to inspect and drive tabs while Electron routes UI requests to backend AI services.

### 4. AI Provider Abstraction
- Unified provider interface supporting streaming chat completions, tool execution, and vision analysis.
- Primary provider: NVIDIA NIM (`https://integrate.api.nvidia.com/v1`) using `meta/llama-3.3-70b-instruct` and `meta/llama-3.2-90b-vision-instruct`.
- Fallback adapter: OpenAI-compatible endpoints with configurable base URL and model ID.
