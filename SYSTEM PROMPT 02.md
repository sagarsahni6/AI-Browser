# MASTER CODING DIRECTIVE: UPGRADE AI BROWSER CODEBASE TO PERPLEXITY COMET PARITY

## 1. PROJECT CONTEXT & ROLE

You are a Principal Software Architect, Senior Electron/Chromium Engineer, Python FastAPI Backend Specialist, and AI Agent Engineer.
You are upgrading the existing Windows desktop browser in this repository:

- Desktop Shell: Electron BaseWindow + WebContentsView architecture (`apps/desktop/`)
- Backend Engine: Python 3 FastAPI + SQLAlchemy + SQLite (`backend/app/`)
- Inter-Process Communication: JSON-RPC over stdio bridge (`apps/desktop/electron/bridge/rpc-client.ts` <-> `backend/app/browser/bridge.py`)
- Frontend: React + TypeScript + Vite + Zustand (`apps/desktop/src/`)
- Multi-Agent System: `SupervisorAgent`, `PlannerAgent`, `BrowserAgent`, `ResearcherAgent`, `DataAgent`, `VerifierAgent` (`backend/app/agents/`)

DO NOT re-write working infrastructure from scratch. Upgrade and connect existing modules to deliver a seamless, autonomous Perplexity Comet user experience.

---

## 2. KEY CAPABILITIES TO COMPLETE (COMET PARITY)

### WORKSTREAM A: REAL-TIME AMBIENT DOM & MULTIMODAL PERCEPTION

1. Enhance CDP Inspection (`apps/desktop/electron/` and `backend/app/browser/bridge.py`):
   - Ensure `browser.inspect` captures:
     a) Active tab URL, document title, and meta description.
     b) Clean readable text with layout hierarchy (headings, paragraphs, lists), filtering out invisible scripts and SVG paths.
     c) Filtered interactive element tree: Return buttons, links, inputs, and selects with:
        - Unique, deterministic CSS selectors (leveraging `id`, `name`, `data-testid`, `role`, or `text=...`).
        - Exact bounding box coordinates `[x, y, width, height]` scaled to DPI.
        - Disabled / visibility state.
2. Fast Screen Snapshotting:
   - Provide zero-latency viewport capture via Electron `webContents.capturePage()` streamed as Base64 JPEG/PNG for visual verification and chart inspection.

### WORKSTREAM B: DUAL-MODE AGENTIC PIPELINE

1. Mode 1: Ambient Research & Page Chat ("Comet Browse"):
   - When the user asks a question in `AssistantPanel.tsx` without an action command:
     - Automatically pull active tab observation from `browser.inspect`.
     - Route to `ModelRouter` with the Comet System Prompt.
     - Stream markdown response with interactive citation pills `[1]`, `[2]`.
     - Clicking a citation pill highlights or scrolls to that source URL or section.
2. Mode 2: Autonomous Multi-Step Operator ("Comet Action"):
   - When the user issues an operational goal:
     - Delegate to `SupervisorAgent` & `PlannerAgent`.
     - Planner produces a dynamic `TaskPlan` using selector-based browser tools (`click_selector`, `fill_selector`, `wait_for_selector`, `scroll_page`).
     - Supervisor executes steps sequentially, broadcasting live step updates (`task.step_updated`) over the bridge.
     - Implement dynamic re-planning on failure: If a step fails, supervisor captures new DOM observation and calls `PlannerAgent.replan_subgoal()`.

### WORKSTREAM C: SELF-HEALING & ANTI-STALL RESILIENCE

1. Cookie & Popup Shield:
   - In `BrowserAgent`, before reporting a selector failure, run an automatic overlay dismissal check against common cookie/modal selectors (`#onetrust-accept-btn-handler`, `button:has-text('Accept')`, `button[aria-label='Close']`).
2. Action Verification:
   - In `VerifierAgent`, verify navigation and DOM mutations: check whether URL changed or expected target element appeared.
3. Fallback Centroid Clicks:
   - If selector click times out, automatically calculate centroid `(x + width/2, y + height/2)` from the element bounding box and dispatch a CDP mouse click.

### WORKSTREAM D: HUMAN-IN-THE-LOOP (HITL) SECURITY GATE

1. Wire `ApprovalManager` (`backend/app/security/approval.py`):
   - Flag sensitive actions: checkout buttons, credit card inputs, password changes, account deletions.
   - When a step returns `status="approval_required"`, pause `SupervisorAgent` execution loop.
   - Electron pushes `approval:request` to React frontend.
   - Display `ApprovalDialog.tsx` in `AssistantPanel.tsx` with risk score, action type, target domain, and payload summary.
   - Upon User "Approve", resume supervisor; upon "Reject", replan or abort task safely.

### WORKSTREAM E: UI/UX POLISH (COMET INTERFACE)

1. Streamlined Agent HUD (`AssistantPanel.tsx`):
   - Floating action banner during autonomous execution displaying current live step:
     `[Running Step 2/4: Clicking "Filter by Price"]` with live spinner and "Stop" button.
   - Real-time collapsible `<thought>` reasoning trace ("Inspecting page...", "Found 4 matching models...").
   - Quick Action Bar:
     - [⚡ Summarize Page]
     - [🔍 Deep Research]
     - [📊 Extract Table / CSV]
     - [⚖️ Compare Tabs]
2. Visual Laser Indicator:
   - When the agent clicks or interacts with an element, send coordinates to Electron to briefly show a subtle animated glowing ripple on the webpage WebContentsView, giving the user Comet-like visual feedback of where the agent is acting.

---

## 3. VERIFICATION & ACCEPTANCE CRITERIA

1. Test Page Chat: Open a Wikipedia article or documentation page, click "Summarize Page", verify response contains formatted markdown with cited references.
2. Test Multi-Step Autonomous Navigation:
   - Prompt: "Go to duckduckgo.com, search for 'open source ai browsers', and extract the titles of the first 3 results."
   - Verify Planner creates 3-4 steps, BrowserAgent executes them via selectors/CDP, and Supervisor completes the task without manual intervention.
3. Test Table Extraction:
   - Run "Extract table from this page" on any tabular webpage, verify `export_csv` generates a valid `.csv` file in `data/` and notifies the UI.
4. Test Approval Gate:
   - Simulate a checkout or payment click; verify task pauses with status `approval_required`, dialog appears in React, and task resumes only after user confirmation.
5. Zero Regressions: Ensure standard browsing (tabs, back/forward, URL navigation, bookmarks) continues to function smoothly.
