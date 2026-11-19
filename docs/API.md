# API Reference

## 1. Internal JSON-RPC 2.0 (stdio)

Transport: JSON Lines over stdin/stdout between Electron and Python.

### Methods: Python -> Electron (Browser Operations)
- `browser.get_tabs`: Returns list of open tabs (`BrowserTab[]`).
- `browser.create_tab`: `{ url?: string }` -> Returns new tab ID string.
- `browser.switch_tab`: `{ tab_id: string }` -> Returns `boolean`.
- `browser.close_tab`: `{ tab_id: string }` -> Returns `boolean`.
- `browser.navigate`: `{ url: string }` -> Returns `boolean`.
- `browser.inspect`: Returns `PageObservation` containing url, title, viewport, visibleText, and interactiveElements.
- `browser.capture_screenshot`: Returns base64 PNG data URL string.

### Methods: Electron -> Python (AI & Orchestration)
- `assistant.chat`: `{ message: string, context?: object }` -> Returns `{ reply: string }`.

---

## 2. Python FastAPI HTTP Endpoints (127.0.0.1)

### Health
- `GET /api/v1/health`
  - Returns backend health, version, database status, and AI provider readiness.

### AI Assistant
- `POST /api/v1/assistant/chat`
  - Request: `{ message: string, conversation_id?: string, tab_id?: string, context?: object }`
  - Response: `{ reply: string, conversation_id: string, model: string }`

### Browser Context
- `GET /api/v1/browser/tabs`
  - Returns current list of tabs from the active browser session.
- `POST /api/v1/browser/context`
  - Returns live CDP observation snapshot of the active tab.

---

## 3. Renderer IPC (window.electronAPI)

Exposed to trusted panels via `electron/preload.ts`:
- `createTab(url?: string): Promise<string>`
- `closeTab(tabId: string): Promise<void>`
- `switchTab(tabId: string): Promise<void>`
- `getTabs(): Promise<BrowserTab[]>`
- `onTabsUpdated(callback): () => void`
- `navigate(url: string): Promise<void>`
- `goBack(): Promise<void>`
- `goForward(): Promise<void>`
- `reload(): Promise<void>`
- `toggleSidebar(): Promise<boolean>`
- `toggleAssistant(): Promise<boolean>`
- `getInitialState(): Promise<AppState>`
- `capturePage(): Promise<string>`
- `inspectPage(): Promise<PageObservation>`
- `onBackendStatus(callback): () => void`
- `sendChatMessage(message: string, context?: object): Promise<string>`
- `onChatStream(callback): () => void`
