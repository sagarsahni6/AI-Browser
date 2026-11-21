# Project: Perplexity Comet Parity Upgrade

## Architecture
- **Backend (Python 3.11 / FastAPI)**:
  - `backend/app/api/assistant.py`: Reads & caches `SYSTEM PROMPT 01.md` at startup, prepends `{"role": "system", "content": <comet_system_prompt>}` to messages list for all chat completions.
  - `backend/app/agents/supervisor.py`: Enriches all 8 `task.step_updated` bridge notification payloads with `total_steps: len(plan.steps)`.
  - `backend/app/agents/browser_agent.py`: Adds third fallback for `click_selector` to execute `centroid_fallback_click` using matched element index from last page observation (`_find_matched_element_index` returns `None` on mismatch, honoring explicit `element_index`).
  - `backend/app/tools/executor.py`: Supports `bounds` coordinate lookup for centroid fallback calculation.
- **Electron Bridge & Shared Types (TypeScript)**:
  - `apps/desktop/electron/browser/page-observer.ts`: Upgrades `extractionScript` to capture deterministic CSS selectors (priority: `#id` > `[data-testid]` > `[name]` > `[aria-label]` > `text=...` > `tag:nth-of-type(n)`), `disabled` state (`el.disabled || el.getAttribute('aria-disabled') === 'true'`), and `metaDescription` from `<meta name="description">`.
  - `shared/contracts/browser.ts`: Adds `selector: string` and `disabled?: boolean` to `InteractiveElement`, and `metaDescription?: string` to `PageObservation`.
  - `shared/ipc/channels.ts`: Confirms `APPROVAL_REQUEST: 'approval:request'` and `APPROVAL_RESPONSE: 'approval:response'`.
  - `apps/desktop/electron/bridge/ipc-handlers.ts`: Enriches chat message context with `metaDescription` and up to 30 `interactiveElements`; broadcasts to `APPROVAL_REQUEST` when step status is `approval_required`; handles `APPROVAL_RESPONSE`; emits `comet:laser-indicator` with `{ x, y }` on click methods.
- **Frontend & Overlay (React 18 / Electron Preload)**:
  - `apps/desktop/electron/preload.ts`: Exposes `onLaserIndicator` via `contextBridge`.
  - `apps/desktop/src/overlay/LaserIndicator.ts`: Implements visual ripple indicator overlay with dynamic keyframes and auto-cleanup.
  - `apps/desktop/src/app/App.tsx`: Wires in `LaserIndicator` overlay lifecycle in root renderer effect.
  - `apps/desktop/src/panels/AssistantPanel.tsx`: Displays active action banner progress as `Running Step {activeAction.step_number || '?'}/{activeAction.total_steps || '?'}: ...`; updates Quick Action chips with emoji prefixes ("⚡ Summarize Page", "🔍 Deep Research", "📊 Extract Table / CSV", "⚖️ Compare Tabs"), preserving secondary actions.
  - `apps/desktop/src/components/ApprovalDialog.tsx`: Adds labeled color-coded risk meter bar above action details (100% red for "RED TIER", 40% yellow for "YELLOW TIER", 20% green otherwise).
  - `apps/desktop/src/vite-env.d.ts` & type declarations: Resolves CSS module imports and store signatures for 0-error `npx tsc --noEmit`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Comet System Prompt Injection | Read and cache `SYSTEM PROMPT 01.md` at startup, prepend to chat completions in `assistant.py` | M1 | R1 |
| 2 | Supervisor Step Tracking | Include `total_steps: len(plan.steps)` in all 8 `task.step_updated` payloads in `supervisor.py` | M1 | R1 |
| 3 | Active Action Step Banner | Display `Running Step {step_number || '?'}/{total_steps || '?'}: ...` in `AssistantPanel.tsx` | M1 | R1 |
| 4 | Deterministic Element Selectors | Generate CSS selectors by priority (`#id` > `[data-testid]` > `[name]` > `[aria-label]` > `text=...` > `tag:nth-of-type(n)`) in `page-observer.ts` | M1 | R2 |
| 5 | Element Disabled State & Meta Description | Extract `disabled` and `metaDescription` in `page-observer.ts` and sanitize | M1 | R2 |
| 6 | Shared TypeScript Types | Update `InteractiveElement` and `PageObservation` in `shared/contracts/browser.ts` | M1 | R2 |
| 7 | Chat Context Enrichment | Enrich chat messages with `metaDescription` and up to 30 `interactiveElements` in `ipc-handlers.ts` | M1 | R2 |
| 8 | Dedicated Approval IPC Channel | Declare `APPROVAL_REQUEST` & `APPROVAL_RESPONSE` in `channels.ts`, broadcast on `approval_required`, register response handler | M1 | R2 |
| 9 | Centroid Fallback Click | Third fallback in `browser_agent.py` using matched element index from last observation, supporting `bounds` in `executor.py` | M1 | R3 |
| 10 | Visual Laser Indicator Emission | Emit `comet:laser-indicator` with `{ x, y }` on successful click in `ipc-handlers.ts` | M1 | R3 |
| 11 | Laser Indicator Overlay & Preload | Expose `onLaserIndicator` in `preload.ts`, implement `LaserIndicator.ts` with ripple animation, wire in `App.tsx` | M1 | R3 |
| 12 | Quick Action Bar Polish | Emoji prefixes on chip labels in `AssistantPanel.tsx`, preserving secondary actions | M1 | R4 |
| 13 | Risk Score Meter Bar | Visual meter in `ApprovalDialog.tsx` (100% red RED TIER, 40% yellow YELLOW TIER, 20% green otherwise) | M1 | R4 |
| 14 | Non-Destructive Preservation & Build Cleanliness | Clean `npx tsc --noEmit` (0 errors), `py_compile` (0 errors), preserve working modules | M1 | R5 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Comet Parity Production Upgrade | Full implementation of R1-R5 across backend, electron bridge, shared types, and frontend | Step 0 Survey | DONE |

## Interface Contracts
### `PageObserver` ↔ `InteractiveElement`
- `selector: string`: Deterministic selector string.
- `disabled?: boolean`: `true` if `el.disabled || el.getAttribute('aria-disabled') === 'true'`.
- `bounds: { x: number, y: number, width: number, height: number }`: Pixel viewport bounding box.

### `SupervisorAgent` ↔ Bridge Notification
- Payload for `"task.step_updated"`:
  ```json
  {
    "task_id": "...",
    "step_id": 1,
    "step_number": 1,
    "total_steps": 5,
    "status": "running | approval_required | completed | failed | paused | cancelled | recovering",
    ...
  }
  ```

### Electron Bridge ↔ Laser Indicator
- Channel: `comet:laser-indicator` (`IPC_CHANNELS.COMET_LASER_INDICATOR`)
- Payload: `{ x: number, y: number }`

### Approval IPC Channel
- Channels: `approval:request` (`IPC_CHANNELS.APPROVAL_REQUEST`) and `approval:response` (`IPC_CHANNELS.APPROVAL_RESPONSE`)
- Request payload: `{ task_id, step_id, status: 'approval_required', reason, action, parameters, total_steps }`
- Response payload: `{ taskId: string, approved: boolean, reason?: string }`

## Code Layout
- `backend/app/api/assistant.py` (caching, system prompt injection)
- `backend/app/agents/supervisor.py` (step tracking)
- `backend/app/agents/browser_agent.py` (centroid fallback)
- `backend/app/tools/executor.py` (bounds coordinate calculation)
- `apps/desktop/electron/browser/page-observer.ts` (CDP extraction script)
- `shared/contracts/browser.ts` (data contracts)
- `shared/ipc/channels.ts` (channel constants)
- `apps/desktop/electron/bridge/ipc-handlers.ts` (bridge handlers)
- `apps/desktop/electron/preload.ts` (preload API)
- `apps/desktop/src/overlay/LaserIndicator.ts` (ripple overlay)
- `apps/desktop/src/app/App.tsx` (renderer entry overlay wiring)
- `apps/desktop/src/panels/AssistantPanel.tsx` (action banner & quick chips)
- `apps/desktop/src/components/ApprovalDialog.tsx` (risk meter bar)
- `apps/desktop/src/vite-env.d.ts` (type declarations)
