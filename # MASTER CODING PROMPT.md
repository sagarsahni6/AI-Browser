# MASTER CODING PROMPT

# BUILD A PRODUCTION-GRADE AI-POWERED AUTONOMOUS DESKTOP BROWSER

## 1. YOUR ROLE

Act as a principal desktop browser architect, senior Electron engineer, senior React/TypeScript developer, Python backend engineer, AI agent engineer, Chromium automation specialist and application security engineer.

Your assignment is to design, implement, test and deliver a complete production-grade Windows desktop browser inspired by the user experience and capabilities of Perplexity Comet.

Do not build a simple browser with a chatbot sidebar.

Build a real desktop Chromium browser with an integrated AI intelligence system capable of understanding webpages, conducting research, controlling the browser and completing multi-step tasks.

The application must have two equally important product capabilities:

**A. AI Research Browser**

- AI-powered search and research.
- Understand the current webpage.
- Summarize articles and websites.
- Answer questions with source citations.
- Compare multiple websites and tabs.
- Extract structured information.
- Remember locally saved research and preferences.

**B. Autonomous Browser Agent**

- Interpret natural-language instructions.
- Plan multi-step browser operations.
- Navigate websites.
- Open and manage browser tabs.
- Click elements.
- Type and fill inputs.
- Scroll through pages.
- Extract information.
- Work across multiple websites.
- Recover from navigation and interaction errors.
- Verify task completion.
- Request user authorization for sensitive actions.

The application must run locally on Windows and must not require a cloud application backend or mandatory user account.

Do not copy Perplexity's branding, logo or proprietary interface assets. Create an original premium browser identity.

---

# 2. LOCKED TECHNOLOGY STACK

Use this architecture throughout the project.

## Desktop

- Electron.
- Chromium bundled with Electron.
- Node.js.
- TypeScript.
- Electron BaseWindow.
- Electron WebContentsView.

## Frontend

- React.
- TypeScript.
- Vite.
- Zustand for frontend state management.
- React Router where useful.
- Lucide icons.
- Modern CSS with design tokens.
- Motion animations where useful.

Do not require Tailwind CSS. Use organized CSS modules or a maintainable design-system approach.

## Backend

- Python 3.
- FastAPI.
- Pydantic v2.
- HTTPX.
- SQLite.
- SQLAlchemy 2.
- Alembic for database migrations.
- Asyncio for asynchronous operations.
- PyInstaller for packaging the Python backend on Windows.

## AI

- NVIDIA NIM as the primary provider.
- OpenAI-compatible provider abstraction.
- Support additional compatible providers.
- Separate text, vision and tool-calling capabilities.
- Streaming responses.
- Structured tool execution.

## Browser automation

- Electron Debugger API.
- Chromium DevTools Protocol.
- DOM inspection.
- Accessibility tree.
- DOM snapshots.
- Screenshot capture.
- Vision-language model integration.

## Testing

- Pytest.
- Vitest.
- Playwright for isolated browser tests and fixture websites.
- Electron integration tests.
- Windows security and installation tests.

Before selecting package versions, check current stable releases, compatibility and security advisories. Pin compatible dependency versions and commit lockfiles. Do not blindly use outdated tutorials.

---

# 3. NON-NEGOTIABLE ARCHITECTURAL RULES

1. This must be a real desktop browser, not a browser simulator.
2. Use real Chromium WebContentsViews for actual webpages.
3. Do not use ordinary iframes to load arbitrary websites.
4. Do not use the deprecated Electron BrowserView API.
5. Do not expose a browser DevTools debugging port to the network.
6. Do not enable Node integration in remote websites.
7. Do not allow AI models to execute arbitrary generated Python, shell commands or unrestricted JavaScript.
8. All browser actions must go through validated tools.
9. Do not store API keys in frontend code.
10. Do not transmit cookies, passwords or authentication tokens to AI models.
11. Do not require cloud synchronization or mandatory registration.
12. Do not implement Chrome extensions in the initial version.
13. Do not use fake sample responses as actual production features.
14. Every major feature must have proper error handling and tests.
15. Keep the application modular and suitable for future commercial distribution.

---

# 4. PRODUCT ARCHITECTURE

Build the application using five major layers.

## Layer 1: Desktop Browser Shell

Responsible for:

- Main application window.
- Browser toolbar.
- Tabs.
- Navigation.
- Address bar.
- Browser sessions.
- WebContentsView lifecycle.
- Browser history.
- Downloads.
- Bookmarks.
- Permissions.
- Window resizing.

Use Electron BaseWindow as the root window where multiple independently managed views are composed.

Create separate WebContentsViews for the browser interface panels and the webpage viewport.

Recommended composition:

- Toolbar and tab panel across the top.
- Navigation sidebar on the left.
- Active Chromium webpage in the central area.
- AI assistant panel on the right.
- Optional status and automation panel.

Each React interface panel can mount the same local frontend application with a panel identifier such as:

- panel=toolbar
- panel=sidebar
- panel=assistant

Use a centralized main-process state and typed IPC events to synchronize these panels.

This architecture must be validated with an early layout prototype before building the complete UI.

Implement responsive resizing through a central layout manager.

Do not assume WebContentsViews automatically follow HTML/CSS layout. The main process must calculate and update their bounds.

Use device-independent window coordinates and account for Windows DPI scaling.

Maintain separate WebContentsViews for browser tabs. Switching tabs must change the active visible page without unnecessarily destroying background tabs.

Implement explicit cleanup of all child WebContentsViews when the BaseWindow closes. BaseWindow does not automatically destroy all child webContents.

## Layer 2: AI Assistant

Responsible for:

- Natural-language conversation.
- Webpage understanding.
- Research.
- Answer generation.
- Tool calling.
- Model selection.
- Conversation history.
- Streaming responses.

## Layer 3: Agent Orchestration

Responsible for:

- Task planning.
- Agent coordination.
- Browser tool selection.
- Task execution.
- Permission checking.
- Retry management.
- Verification.
- Cancellation.

## Layer 4: Browser Automation Engine

Responsible for:

- DOM observation.
- Accessibility inspection.
- Visual inspection.
- User-like mouse and keyboard events.
- Navigation.
- Extraction.
- Result verification.

## Layer 5: Local Data and Security

Responsible for:

- SQLite database.
- Settings.
- Browser profiles.
- Conversation persistence.
- Task logs.
- Local memory.
- API key protection.
- Permission records.

---

# 5. USER INTERFACE REQUIREMENTS

Create a premium, polished, modern desktop browser.

Design direction:

- Premium minimal interface.
- Dark and light themes.
- Carefully spaced layouts.
- Rounded panels.
- Subtle borders.
- Elegant icons.
- Smooth animations.
- Professional typography.
- Excellent readability.
- Responsive panels.
- Keyboard accessibility.

Avoid making it look like a generic admin dashboard.

## Main browser layout

### A. Top browser toolbar

Implement:

- Back.
- Forward.
- Reload.
- Stop loading.
- Home.
- Address and search bar.
- Security indicator.
- Bookmark button.
- Downloads.
- New tab.
- Active tab controls.
- AI assistant toggle.
- Settings.

Address bar behavior:

- Accept website URLs.
- Accept search queries.
- Detect URLs intelligently.
- Display current URL.
- Support paste and navigation.
- Provide suggestions from local history and bookmarks.
- Show loading progress.
- Display website security state.

Use a configurable search provider.

### B. Tab management

Support:

- Multiple tabs.
- New tab.
- Close tab.
- Switch tabs.
- Reorder tabs.
- Duplicate tabs.
- Pin tabs.
- Restore recently closed tabs.
- Tab loading indicators.
- Tab titles.
- Favicons.
- Keyboard shortcuts.
- Background tab lifecycle.

Add a clean new-tab page with an AI-powered search field.

### C. Left sidebar

Include:

- Home.
- AI Search.
- Browser history.
- Bookmarks.
- Downloads.
- Saved pages.
- Research collections.
- Recent AI tasks.
- Settings.

The sidebar should be collapsible.

### D. Main webpage area

Display actual remote webpages through WebContentsView.

Support:

- Full browsing.
- Normal navigation.
- Scroll.
- Text selection.
- Context menu.
- Find in page.
- Downloads.
- Popup handling.
- Browser back and forward history.
- Browser zoom.

Do not compromise ordinary browsing functionality to support AI.

### E. Right AI assistant sidebar

Build a complete assistant interface.

Features:

- New conversation.
- Chat history.
- Message streaming.
- Current webpage context.
- Selected text context.
- Multiple-tab context.
- Screenshot analysis.
- Source citations.
- Suggested questions.
- Copy response.
- Regenerate response.
- Stop generation.
- Clear conversation.
- Model selector.

Context buttons:

- Ask about this page.
- Summarize this page.
- Compare open tabs.
- Extract important information.
- Generate a report.
- Start browser automation.

### F. Automation activity interface

Create a separate live automation view.

Display:

- Active task name.
- Task status.
- Current step.
- Completed steps.
- Current browser tab.
- Actions being performed.
- Pending approvals.
- Errors.
- Stop button.
- Final task report.

The AI must never operate invisibly. Users should be able to see what it is doing and stop it.

---

# 6. NVIDIA NIM AND MULTI-PROVIDER AI ARCHITECTURE

Build a provider-independent AI service.

The primary provider is NVIDIA NIM.

Support optional additional AI providers through adapters.

Do not hardcode one particular model throughout the application.

## Provider interface

Create a common abstraction with methods equivalent to:

- chat_completion()
- stream_completion()
- execute_tool_call()
- analyze_image()
- list_models()
- check_connection()
- get_capabilities()

Create adapters:

backend/ai/providers/

- base.py
- nvidia_nim.py
- openai_compatible.py
- registry.py
- capabilities.py

The OpenAI-compatible adapter should accept configurable provider base URLs, API keys and model IDs.

Only enable model capabilities that have actually been verified.

A model may support text generation without supporting images or tool calls. The application must check this instead of assuming that every model supports every capability.

## NVIDIA NIM configuration

Support:

NVIDIA_BASE_URL
NVIDIA_API_KEY
NVIDIA_MODEL

Use the OpenAI-compatible chat-completions interface where supported.

Standard API:

POST /v1/chat/completions

Model discovery:

GET /v1/models

Support:

- Streaming.
- Message history.
- Tool definitions.
- Tool call responses.
- Tool result messages.
- Vision requests when the selected model supports them.
- Timeout handling.
- Rate limits.
- Retry policies.

Never hardcode a discontinued or unavailable model ID.

Allow users to configure their own model IDs.

## AI model routing

Introduce a ModelRouter.

Example:

User asks a simple factual question:
Use an appropriate text model.

User requests screenshot analysis:
Use a vision-capable model.

User requests autonomous browser control:
Use a model that supports reliable structured tool calling.

User requests deep research:
Use the research workflow and an appropriate reasoning model.

Allow the user to override automatic model selection.

Implement connection testing and clear error messages.

## Secret management

Use Electron safeStorage on Windows to protect API credentials using the operating system's secure storage facilities.

The main process should own credential storage.

Do not store keys in:

- React state.
- Frontend localStorage.
- SQLite plaintext columns.
- Logs.
- Git repositories.
- Packaged source files.

In production, pass required secrets to the Python process over a protected process channel and retain them in memory only as needed.

In development, allow environment variables through a documented .env.example file.

Never commit actual credentials.

---

# 7. PYTHON FASTAPI BACKEND

The Python application is responsible for AI processing and agent orchestration.

Suggested modules:

- FastAPI application.
- AI provider registry.
- Model router.
- Supervisor agent.
- Research agent.
- Browser agent.
- Data extraction agent.
- Verification agent.
- Permission manager.
- Task queue.
- Search provider registry.
- Database service.
- Logging service.

The backend must remain independent of the React frontend.

Use Pydantic models for every API request and response.

Do not accept arbitrary browser commands directly from the model.

Implement strict input validation, error handling and timeouts.

## Backend endpoints

Implement these routes.

### Health

GET /api/v1/health

Returns:

- Backend version.
- Backend status.
- Database status.
- AI provider status.

### AI assistant

POST /api/v1/assistant/chat

Supports:

- User message.
- Conversation ID.
- Current tab context.
- Optional selected text.
- Model selection.
- Streaming response.

### Conversations

GET /api/v1/conversations

POST /api/v1/conversations

GET /api/v1/conversations/{id}

DELETE /api/v1/conversations/{id}

### Agent tasks

POST /api/v1/agent/tasks

GET /api/v1/agent/tasks

GET /api/v1/agent/tasks/{id}

POST /api/v1/agent/tasks/{id}/approve

POST /api/v1/agent/tasks/{id}/reject

POST /api/v1/agent/tasks/{id}/cancel

### Browser context

POST /api/v1/browser/context

GET /api/v1/browser/tabs

### AI providers

GET /api/v1/providers

POST /api/v1/providers/test

GET /api/v1/providers/models

### Search

POST /api/v1/search

GET /api/v1/search/providers

### Progress

Provide a streaming task event interface using Server-Sent Events or an equivalent authenticated mechanism.

Events should include:

- task.started
- task.planned
- step.started
- step.completed
- step.failed
- approval.required
- browser.action
- verification.completed
- task.completed
- task.cancelled

All responses must use predictable schemas.

---

# 8. ELECTRON AND PYTHON PROCESS COMMUNICATION

The Electron main process is the only authority allowed to control browser WebContentsViews.

The React interface must never communicate directly with remote webpage processes.

Implement a typed application bridge.

## Process architecture

Electron main process:

- Creates the main application window.
- Creates WebContentsViews.
- Manages tabs.
- Controls navigation.
- Owns browser sessions.
- Receives renderer IPC.
- Starts and stops the Python process.
- Manages secure credentials.
- Validates browser automation commands.

Python process:

- Starts FastAPI on an available localhost-only port.
- Runs the AI agents.
- Sends browser action requests.
- Returns task progress.
- Manages the database.
- Manages AI provider integrations.

## Local communication

In production:

1. Electron launches the packaged Python backend.
2. Electron generates a cryptographically random local authentication token.
3. Pass required startup credentials and configuration through a controlled startup channel.
4. Python starts FastAPI bound exclusively to 127.0.0.1.
5. Python communicates its ready status and local port through a structured startup message.
6. Electron owns all requests originating from the renderer.
7. All backend requests require authentication.
8. The Python agent requests browser actions through a bidirectional JSON-RPC 2.0 protocol over the spawned process's standard streams.

Use JSON Lines over stdin/stdout for process RPC.

Important:

- stdout is reserved exclusively for protocol messages.
- stderr is reserved for diagnostic logs.
- Every RPC request has a unique ID.
- Every request has a timeout.
- Support cancellation.
- Reject unknown RPC methods.
- Validate every request and response.
- Prevent duplicate execution of non-idempotent operations.

Do not expose the stdio bridge to webpages.

Do not expose the FastAPI server to LAN interfaces.

Do not place secrets in process command-line arguments.

---

# 9. BROWSER CONTROL ENGINE

This is one of the most important modules.

Build a reliable automation interface around Electron WebContentsView and each tab's webContents.

Production control must use the Electron main-process Debugger API and supported Chromium DevTools Protocol commands.

Do not expose the remote-debugging listener.

Implement:

backend/browser/

- browser_bridge.py
- browser_protocol.py
- action_schemas.py
- context_models.py

apps/desktop/electron/browser/

- browser-manager.ts
- tab-manager.ts
- debugger-manager.ts
- cdp-client.ts
- page-observer.ts
- page-actions.ts
- screenshot-manager.ts

## A. Browser observation

Implement a browser context tool that returns:

- Current tab ID.
- Current URL.
- Current title.
- Current viewport dimensions.
- Loading status.
- Visible webpage text.
- Relevant accessibility information.
- Important interactive elements.
- Form controls.
- Link information.
- Screenshot metadata.

Use:

- DOMSnapshot.captureSnapshot.
- DOM.getDocument.
- Accessibility information from supported CDP domains.
- Visible DOM information.
- Page metadata.
- webContents.capturePage().

Check protocol support against the Electron-bundled Chromium version. Do not rely on obsolete CDP methods.

## B. DOM-based automation

The AI must be able to identify:

- Buttons.
- Text inputs.
- Textareas.
- Checkboxes.
- Radio buttons.
- Select elements.
- Links.
- Search fields.
- Tables.
- Forms.
- Interactive controls.

Give each detected element a temporary element identifier.

The identifier should be linked to:

- Tab ID.
- Current page navigation state.
- Element locator.
- Relevant element metadata.
- Bounding box.
- Available actions.

Reject stale identifiers after major navigation or DOM changes.

Use accessibility semantics and DOM information before resorting to coordinates.

## C. Browser actions

Create validated actions:

- navigate
- go_back
- go_forward
- reload
- stop_loading
- create_tab
- switch_tab
- close_tab
- capture_page
- get_page_context
- click_element
- type_text
- fill_input
- select_option
- scroll_page
- press_key
- extract_text
- extract_links
- extract_table
- wait_for_navigation
- find_element

Use a fixed tool registry and strict JSON input schemas.

For actual interaction, prefer user-like input events through supported CDP Input commands.

Do not let the model create arbitrary JavaScript selectors or scripts and execute them unchecked.

Provide bounded, prewritten DOM-observation helpers where necessary.

Implement action result verification.

Example:

AI action:
Click the Search button.

Execution:

1. Identify the correct button.
2. Confirm that the button is visible and unique.
3. Determine its position.
4. Dispatch the click through the controlled browser input interface.
5. Observe the result.
6. Confirm navigation or an expected UI state.
7. Report success or failure.

## D. Screenshot and vision automation

Implement a second automation approach.

Capture the current visible browser viewport using Electron's capturePage.

The vision pipeline should:

1. Capture a screenshot.
2. Mask sensitive inputs.
3. Resize and compress when appropriate.
4. Send the image to a configured vision-capable model only under the user's active context-sharing settings.
5. Identify relevant visual targets.
6. Return a structured action suggestion.
7. Validate coordinates against the current viewport.
8. Execute through the controlled browser action service.
9. Capture a new screenshot.
10. Verify the expected visual change.

Vision should be a fallback or complementary observation method, not the default for every click.

Do not trust visual coordinate predictions without validating bounds and page state.

## E. Combined DOM + Vision strategy

Implement an automation strategy selector.

Preferred sequence:

1. Observe accessibility tree.
2. Inspect relevant DOM nodes.
3. Resolve target semantically.
4. Execute DOM-grounded action.
5. Verify.
6. If the element cannot be located, capture a screenshot.
7. Use visual understanding to propose a bounded target.
8. Revalidate page state.
9. Execute and verify.

The agent must know when automation is uncertain.

Do not pretend an action succeeded merely because an input command was sent.

## F. Browser navigation and session management

Support:

- Persistent default user profile.
- Temporary private browsing session.
- Browser cache management.
- Download directory.
- Cookies retained in the browser's normal local profile.
- User-controlled per-site permissions.
- New-window interception.
- Popup handling.
- Safe external protocol handling.

Never export cookies or login tokens into AI messages.

Do not attempt to bypass CAPTCHAs, MFA, login challenges or website access controls.

When authentication or a security challenge requires user involvement, pause and request user action.

---

# 10. AUTONOMOUS MULTI-AGENT SYSTEM

Implement an agent system with a supervisor.

Do not implement six expensive LLM calls for every small task.

Use one main orchestration agent and lightweight specialist services.

## Supervisor Agent

Responsibilities:

- Understand user intent.
- Classify the requested task.
- Create a structured plan.
- Select the appropriate tools.
- Decide when specialist services are needed.
- Monitor progress.
- Request approval.
- Handle failure.
- Verify final results.

## Research Agent

Responsibilities:

- Search for information.
- Read relevant web sources.
- Extract key facts.
- Compare information.
- Organize research findings.
- Attach source URLs.

## Browser Agent

Responsibilities:

- Observe browser state.
- Select browser tabs.
- Interact with webpages.
- Navigate.
- Click and type.
- Handle scrolling.
- Execute validated actions.

## Data Agent

Responsibilities:

- Extract information.
- Parse tables.
- Normalize fields.
- Compare results.
- Generate structured JSON.
- Produce CSV or report data.

## Verification Agent

Responsibilities:

- Check whether the task was completed.
- Validate extracted information.
- Verify navigation.
- Detect missing fields.
- Detect conflicting results.
- Flag uncertain outcomes.

## Permission Manager

Responsibilities:

- Classify operations.
- Determine whether approval is required.
- Enforce user permissions.
- Pause pending tasks.
- Record approval decisions.

## Agent execution loop

Implement the following loop:

OBSERVE
  ↓
UNDERSTAND
  ↓
PLAN
  ↓
CHECK PERMISSIONS
  ↓
SELECT TOOL
  ↓
EXECUTE
  ↓
OBSERVE AGAIN
  ↓
VERIFY
  ↓
CONTINUE OR REPORT

Use structured task plans.

Example plan:

{
  "task": "Compare prices of a product",
  "steps": [
    {
      "id": 1,
      "action": "open_search",
      "status": "pending"
    },
    {
      "id": 2,
      "action": "visit_source",
      "status": "pending"
    },
    {
      "id": 3,
      "action": "extract_product_data",
      "status": "pending"
    },
    {
      "id": 4,
      "action": "compare_results",
      "status": "pending"
    },
    {
      "id": 5,
      "action": "verify_sources",
      "status": "pending"
    }
  ]
}

Use Pydantic models to validate the actual plan.

Implement:

- Maximum step count.
- Maximum execution time.
- Per-tool timeout.
- Model call budget.
- Token budget.
- Retry limits.
- Cancellation tokens.
- Task state persistence.
- Error recovery.

The agent must never enter an infinite tool execution loop.

---

# 11. BROWSER AI TOOL REGISTRY

Create a centralized, versioned tool registry.

Suggested tools:

Browser:

- get_current_tab
- get_open_tabs
- navigate
- open_new_tab
- switch_tab
- close_tab
- go_back
- go_forward
- reload_page

Observation:

- get_page_content
- get_accessibility_tree
- get_interactive_elements
- take_screenshot
- find_element
- get_page_metadata

Interaction:

- click_element
- type_text
- fill_input
- select_option
- press_key
- scroll_page

Extraction:

- extract_text
- extract_links
- extract_table
- extract_product_information
- extract_contact_information

Research:

- search_web
- visit_source
- summarize_page
- compare_tabs
- compare_sources

Files:

- download_file
- export_csv
- export_json
- export_report

All tools must:

- Have JSON schemas.
- Validate inputs.
- Validate current tab state.
- Have execution timeouts.
- Return structured results.
- Produce auditable logs.
- Have a permission classification.

Never allow the language model to call unrestricted operating-system functions.

---

# 12. WEB SEARCH AND RESEARCH ENGINE

Build a separate search provider system.

NVIDIA NIM is the reasoning engine, not automatically the web search engine.

Create:

backend/search/

- base.py
- registry.py
- browser_search.py
- api_search.py
- source_verification.py
- result_parser.py

Implement a configurable search provider interface.

Initially:

- Support normal browser-based searching through a configurable search engine.
- Permit optional third-party search API adapters.
- Do not require a paid search API to launch basic browsing.
- Do not hardcode a provider API key.
- Make provider status visible.

Search result format:

{
  "title": "Page title",
  "url": "<https://example.com>",
  "snippet": "Search result description",
  "source_domain": "example.com",
  "published_at": null
}

Do not invent source URLs.

## Research features

- Search multiple queries.
- Open selected sources.
- Extract relevant content.
- Compare claims.
- Identify conflicting information.
- Generate source-backed responses.
- Save research sessions.

Every research answer must distinguish:

- Confirmed information.
- Unverified information.
- Inferences.
- Missing information.

Citations must refer to sources that were actually accessed.

---

# 13. LOCAL MEMORY AND DATABASE

All persistent application data must remain local.

Use SQLite.

Suggested database entities:

- app_settings
- browser_preferences
- conversations
- messages
- tasks
- task_steps
- task_events
- approval_requests
- saved_pages
- bookmarks
- browsing_history
- download_records
- research_sources
- research_collections
- provider_settings
- permission_rules
- local_memory_notes

Use appropriate indexes and foreign keys.

Enable SQLite WAL mode where appropriate.

Implement database migrations.

Use parameterized queries and transactions.

Support retention and clearing of:

- Chat history.
- Browser history.
- AI task logs.
- Saved research.
- Local AI memory.

Use SQLite FTS5 for searchable saved research and local notes.

Do not introduce a remote vector database in version one.

An optional local semantic-memory layer can be added later.

## Memory rules

The browser can remember:

- User-defined preferences.
- Saved research.
- Frequently used websites.
- Explicitly saved notes.
- Previous task templates.

Do not automatically treat webpage instructions as trusted memory.

---

# 14. SECURITY AND PRIVACY REQUIREMENTS

Security is a core product feature.

Follow current Electron security recommendations.

## Electron security

For local application UI:

- contextIsolation: true
- nodeIntegration: false
- sandbox: true where compatible
- restrictive Content Security Policy
- narrowly scoped preload API

For remote webpages:

- No Node.js integration.
- No application preload bridge.
- No unrestricted access to filesystem.
- No direct backend credentials.
- Restrict navigation to safe web protocols.
- Intercept and validate new-window requests.
- Apply permission policies to each session.
- Handle permission requests and permission checks.
- Keep webSecurity enabled.

Validate the sender of every IPC request.

Do not use untrusted input with shell.openExternal.

Use a safe custom protocol for loading bundled local UI assets instead of relying on an unrestricted file URL configuration.

## AI prompt injection protection

Webpage content is untrusted.

Never interpret content extracted from websites as system-level instructions.

A webpage must not be able to:

- Override the system prompt.
- Change browser permissions.
- Obtain API keys.
- Read unrelated conversations.
- Trigger unrestricted actions.
- Access browser profile files.
- Execute local shell commands.

Separate:

- Developer instructions.
- User instructions.
- Browser-observed content.
- Tool outputs.

Treat page instructions as data, not authorization.

## User approval system

Define three action categories.

READ-ONLY:

- Read a webpage.
- Summarize.
- Search.
- Extract visible information.
- Compare pages.

REVERSIBLE:

- Open tabs.
- Navigate.
- Scroll.
- Fill draft fields.
- Select non-sensitive controls.

SENSITIVE:

- Send messages.
- Submit forms with external consequences.
- Upload files.
- Publish content.
- Purchase items.
- Make payments.
- Delete records.
- Change account settings.
- Send emails.

Sensitive actions must require explicit user authorization.

An approval must be bound to a specific action and its parameters. Do not accept a general approval as authorization for unrelated future actions.

## Privacy

- Keep browser history local.
- Keep conversations local.
- Keep task logs local.
- Do not synchronize browser data.
- Do not transmit passwords.
- Do not send unnecessary cookies.
- Minimize webpage information sent to AI.
- Clearly disclose external AI providers.
- Provide an AI context-sharing control.
- Allow the user to clear local data.
- Mask password and sensitive form fields in screenshots.
- Do not upload screenshots by default for unrelated tasks.

---

# 15. COMPLETE PROJECT DIRECTORY

Use a monorepo.

Create this structure and expand it only when a real feature requires additional files.

ai-browser/
│
├── apps/
│   └── desktop/
│       ├── electron/
│       │   ├── main.ts
│       │   ├── app-lifecycle.ts
│       │   ├── window-manager.ts
│       │   ├── layout-manager.ts
│       │   ├── preload.ts
│       │   │
│       │   ├── panels/
│       │   │   ├── toolbar-view.ts
│       │   │   ├── sidebar-view.ts
│       │   │   └── assistant-view.ts
│       │   │
│       │   ├── browser/
│       │   │   ├── browser-manager.ts
│       │   │   ├── tab-manager.ts
│       │   │   ├── navigation-manager.ts
│       │   │   ├── session-manager.ts
│       │   │   ├── debugger-manager.ts
│       │   │   ├── cdp-client.ts
│       │   │   ├── page-observer.ts
│       │   │   ├── page-actions.ts
│       │   │   └── screenshot-manager.ts
│       │   │
│       │   ├── bridge/
│       │   │   ├── ipc-handlers.ts
│       │   │   ├── rpc-client.ts
│       │   │   ├── process-manager.ts
│       │   │   └── event-router.ts
│       │   │
│       │   ├── security/
│       │   │   ├── permissions.ts
│       │   │   ├── navigation-guard.ts
│       │   │   ├── sender-validator.ts
│       │   │   └── secret-storage.ts
│       │   │
│       │   └── downloads/
│       │
│       ├── src/
│       │   ├── app/
│       │   ├── components/
│       │   ├── panels/
│       │   ├── browser/
│       │   ├── tabs/
│       │   ├── addressbar/
│       │   ├── ai-assistant/
│       │   ├── automation/
│       │   ├── research/
│       │   ├── history/
│       │   ├── bookmarks/
│       │   ├── downloads/
│       │   ├── settings/
│       │   ├── store/
│       │   ├── hooks/
│       │   ├── styles/
│       │   ├── types/
│       │   └── main.tsx
│       │
│       ├── tests/
│       └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   │
│   │   ├── api/
│   │   │   ├── assistant.py
│   │   │   ├── conversations.py
│   │   │   ├── browser.py
│   │   │   ├── tasks.py
│   │   │   ├── providers.py
│   │   │   └── search.py
│   │   │
│   │   ├── agents/
│   │   │   ├── supervisor.py
│   │   │   ├── planner.py
│   │   │   ├── researcher.py
│   │   │   ├── browser_agent.py
│   │   │   ├── data_agent.py
│   │   │   ├── verifier.py
│   │   │   ├── orchestrator.py
│   │   │   └── task_state.py
│   │   │
│   │   ├── ai/
│   │   │   ├── base.py
│   │   │   ├── router.py
│   │   │   ├── registry.py
│   │   │   ├── capabilities.py
│   │   │   ├── tool_loop.py
│   │   │   └── providers/
│   │   │       ├── nvidia_nim.py
│   │   │       └── openai_compatible.py
│   │   │
│   │   ├── browser/
│   │   │   ├── bridge.py
│   │   │   ├── protocol.py
│   │   │   ├── schemas.py
│   │   │   ├── observation.py
│   │   │   ├── dom_reader.py
│   │   │   ├── accessibility.py
│   │   │   ├── visual_agent.py
│   │   │   ├── actions.py
│   │   │   └── verification.py
│   │   │
│   │   ├── search/
│   │   │   ├── base.py
│   │   │   ├── registry.py
│   │   │   ├── browser_search.py
│   │   │   └── source_verification.py
│   │   │
│   │   ├── security/
│   │   │   ├── permissions.py
│   │   │   ├── approval.py
│   │   │   ├── injection_guard.py
│   │   │   ├── secret_policy.py
│   │   │   └── redaction.py
│   │   │
│   │   ├── database/
│   │   │   ├── engine.py
│   │   │   ├── models.py
│   │   │   ├── repository.py
│   │   │   └── migrations/
│   │   │
│   │   ├── tools/
│   │   │   ├── registry.py
│   │   │   ├── definitions.py
│   │   │   ├── executor.py
│   │   │   └── validation.py
│   │   │
│   │   └── services/
│   │       ├── conversation_service.py
│   │       ├── research_service.py
│   │       ├── task_service.py
│   │       └── export_service.py
│   │
│   ├── tests/
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── .env.example
│
├── shared/
│   ├── contracts/
│   ├── ipc/
│   ├── rpc/
│   ├── schemas/
│   └── constants/
│
├── scripts/
│   ├── setup-dev.ps1
│   ├── build-backend.ps1
│   ├── build-desktop.ps1
│   └── package-windows.ps1
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SECURITY.md
│   ├── API.md
│   ├── DEVELOPMENT.md
│   └── RELEASE.md
│
├── .gitignore
├── README.md
└── package.json

The directory structure is a starting point. Keep the actual implementation clean, testable and modular.

---

# 16. REQUIRED IMPLEMENTATION PHASES

Do not try to implement everything in one unverified step.

Build in the following order.

## PHASE 0 — Repository inspection and architecture spike

Tasks:

1. Inspect the existing repository.
2. Identify installed tools and runtimes.
3. Create the monorepo structure.
4. Configure TypeScript and Python environments.
5. Configure Electron and Vite.
6. Create an initial BaseWindow.
7. Render the trusted toolbar panel.
8. Create a WebContentsView showing a test webpage.
9. Prove that page bounds and layout update correctly.
10. Prove that the Electron debugger can attach and retrieve safe page information.
11. Prove that screenshot capture works.
12. Prove that the Python sidecar can communicate with Electron through JSON-RPC.

Deliver:

- Working desktop prototype.
- Architecture documentation.
- Build instructions.
- Successful smoke tests.

Do not proceed until the browser-view composition and Python bridge work.

## PHASE 1 — Core browser

Implement:

- Browser shell.
- Address bar.
- Navigation.
- Tabs.
- Multiple WebContentsViews.
- Tab switching.
- History.
- Bookmarks.
- Downloads.
- Browser context menu.
- Keyboard shortcuts.
- Session persistence.
- Private session.
- Loading indicators.
- Error pages.

Acceptance:
The application must work as an ordinary Chromium desktop browser even when the AI backend is unavailable.

## PHASE 2 — Database and backend

Implement:

- Python backend.
- FastAPI routes.
- SQLite database.
- Migrations.
- Local authentication.
- Electron sidecar lifecycle.
- Typed RPC.
- Frontend-to-backend communication.
- Error reporting.

Acceptance:
The desktop browser must launch, manage the backend and shut it down cleanly.

## PHASE 3 — AI assistant

Implement:

- NVIDIA NIM client.
- Additional provider adapter.
- Model registry.
- API key storage.
- Connection testing.
- Streaming chat.
- Conversation history.
- Current-page context.
- Page summaries.
- Selected-text questions.
- Local settings.

Acceptance:
A user can open a webpage and ask useful questions about its actual content.

## PHASE 4 — Browser intelligence

Implement:

- Accessibility tree inspection.
- DOM snapshots.
- Interactive element extraction.
- Page context filtering.
- Tab context collection.
- Current page summarization.
- Multi-tab summarization.
- Multi-tab comparison.
- Screenshot capture.

Acceptance:
The AI must understand multiple live webpages without relying on manually pasted content.

## PHASE 5 — DOM automation

Implement:

- Structured browser tools.
- Element identification.
- Click.
- Type.
- Fill.
- Scroll.
- Navigation.
- Form interaction.
- Tab switching.
- Navigation detection.
- Action verification.
- Cancellation.

Acceptance:
The agent should complete a multi-step task on controlled test websites and accurately report the result.

## PHASE 6 — Vision automation

Implement:

- Screenshot pipeline.
- Sensitive input masking.
- Vision provider selection.
- Visual target identification.
- Coordinate validation.
- Visual fallback.
- Action verification.

Acceptance:
The agent must be able to handle selected UI controls that are difficult to identify through DOM inspection.

## PHASE 7 — Multi-agent system

Implement:

- Supervisor.
- Planner.
- Researcher.
- Browser agent.
- Data agent.
- Verifier.
- Approval manager.
- Task persistence.
- Live task events.
- Recovery.
- Cancellation.

Acceptance:
The AI should execute a multi-step task, explain progress and verify the final result.

## PHASE 8 — Search and research

Implement:

- Search providers.
- Browser-native search.
- Search results extraction.
- Source selection.
- Source opening.
- Research summaries.
- Source citations.
- Comparison reports.
- Saved research collections.

Acceptance:
Research responses must include relevant real source links and must not invent facts or citations.

## PHASE 9 — Production hardening

Implement:

- Security audit.
- Permission enforcement.
- Prompt injection testing.
- Memory and performance testing.
- Crash handling.
- Backend recovery.
- Installer generation.
- Application icon.
- Windows shortcuts.
- Uninstaller.
- Logging.
- Error diagnostics.
- Version management.

Acceptance:
The application installs and runs on a clean supported Windows environment.

---

# 17. AUTOMATION USER EXPERIENCE

Implement the following workflow.

User enters:

"Open the three websites I have bookmarked, find their latest product prices, compare them and create a CSV file."

The system:

1. Understands the request.
2. Identifies the three websites.
3. Creates an execution plan.
4. Displays the plan.
5. Opens the required tabs.
6. Inspects each website.
7. Finds relevant product pages.
8. Extracts available price information.
9. Records the source URL and extraction timestamp.
10. Validates extracted values.
11. Compares the collected data.
12. Creates a CSV file.
13. Shows the generated file location.
14. Produces a final report.

Do not claim that the browser extracted information when extraction failed.

Show individual step statuses.

Allow the user to:

- Pause.
- Resume.
- Cancel.
- Approve.
- Reject.
- Inspect actions.

---

# 18. PERFORMANCE REQUIREMENTS

Build a responsive desktop application.

Focus on:

- Fast startup.
- Smooth tab switching.
- Efficient page rendering.
- Limited backend overhead.
- Asynchronous AI requests.
- Cancellation of unused model requests.
- Controlled screenshot size.
- DOM context compression.
- Memory cleanup.
- Background-tab management.
- SQLite indexing.
- Lazy-loading of nonessential UI components.

Do not send an entire page's DOM to an AI model by default.

Extract only relevant visible content.

Set maximum context sizes and truncation strategies.

Keep the browser usable while the backend processes AI requests.

If the backend crashes, the browser must remain usable and provide a restart mechanism.

---

# 19. TESTING REQUIREMENTS

Testing is mandatory.

## Frontend tests

Test:

- Toolbar components.
- Tabs.
- Address bar.
- Assistant panel.
- Settings.
- Task events.
- Approval dialogs.
- Error states.

## Electron tests

Test:

- Application startup.
- Window lifecycle.
- WebContentsView lifecycle.
- Navigation.
- Tab creation.
- Tab deletion.
- Tab switching.
- Browser permissions.
- IPC validation.
- Debugger attachment.
- Backend startup and shutdown.
- Window resizing.
- Resource cleanup.

## Backend tests

Test:

- FastAPI routes.
- NVIDIA provider adapter.
- Alternative provider adapter.
- Model routing.
- Tool schemas.
- Agent planning.
- Task persistence.
- Cancellation.
- Permission decisions.
- SQLite migrations.
- RPC bridge.

Mock API responses in unit tests.

Never make the standard test suite depend on paid AI API calls.

## Browser automation tests

Create controlled fixture websites with:

- Search forms.
- Login-like test forms.
- Tables.
- Buttons.
- Links.
- Dropdowns.
- Dynamic content.
- Modal dialogs.
- Nested frames.
- Long scrolling pages.
- Delayed navigation.

Test:

- DOM identification.
- DOM clicking.
- Input filling.
- Table extraction.
- Screenshot capture.
- Vision fallback.
- Action verification.
- Timeout recovery.

## Security tests

Test:

- Malicious webpage content.
- Prompt injection.
- Renderer IPC spoofing.
- Unauthorized backend requests.
- Invalid URLs.
- File protocol access.
- Dangerous external schemes.
- API key leakage.
- Screenshot redaction.
- Unauthorized sensitive actions.
- Localhost service exposure.
- Debugger endpoint exposure.
- Malformed tool inputs.

All security-critical tests must pass before a production release.

---

# 20. WINDOWS BUILD AND DISTRIBUTION

Deliver a Windows x64 desktop application.

Use electron-builder with NSIS packaging.

Build pipeline:

1. Install Node dependencies.
2. Build the React application.
3. Compile Electron TypeScript.
4. Package the Python backend.
5. Copy backend assets into application resources.
6. Run production configuration checks.
7. Generate the Windows installer.
8. Verify installation.
9. Verify the uninstaller.
10. Test application launch on a clean Windows environment.

The packaged backend must run without requiring the user to install Python separately.

Provide:

- Windows installer.
- Application icon.
- Version information.
- Installation guide.
- Uninstallation support.
- First-run setup.
- NVIDIA API key setup instructions.

Prepare for Windows code signing.

Do not invent signing credentials.

Allow unsigned development builds and document the additional release configuration needed for signed commercial distributions.

Keep application updates as a future release feature unless a secure update pipeline is fully implemented.

---

# 21. SETTINGS AND FIRST-RUN EXPERIENCE

On first launch, show a setup wizard.

Step 1:
Welcome and product introduction.

Step 2:
Choose default search engine.

Step 3:
Configure NVIDIA NIM API key.

Step 4:
Choose the default AI model.

Step 5:
Test the AI connection.

Step 6:
Configure optional additional AI provider.

Step 7:
Explain local storage and AI context sharing.

Step 8:
Complete setup and open the browser.

Settings should include:

General:

- Startup behavior.
- Default search engine.
- Downloads directory.
- Theme.
- Default zoom.

AI:

- Provider selection.
- Model selection.
- API configuration.
- Temperature where supported.
- Vision capability.
- Context sharing.
- Token limits.

Automation:

- Automation permissions.
- Approval policy.
- Maximum task steps.
- Maximum task time.
- Automation notifications.

Privacy:

- Clear browser history.
- Clear conversations.
- Clear AI task records.
- Clear saved research.
- Screenshot sharing preferences.
- Local memory controls.

Advanced:

- Backend diagnostic status.
- Application logs.
- Reset settings.
- Restart backend.
- Export diagnostics.

---

# 22. ERROR HANDLING

Every feature must have a clear failure state.

Handle:

- NVIDIA API unavailable.
- Incorrect API key.
- Unsupported model.
- Model timeout.
- Rate limits.
- Network interruption.
- Search provider failure.
- Navigation failure.
- Website unavailable.
- Element not found.
- Stale element identifier.
- Screenshot capture failure.
- Vision provider unavailable.
- Browser debugger detached.
- Backend crash.
- Database error.
- Invalid JSON tool response.
- Automation timeout.
- User cancellation.

Never silently swallow errors.

Never mark failed tasks as successful.

Provide retry options only when retrying is safe.

---

# 23. FUTURE-COMPATIBLE DESIGN

Do not implement these in version one, but avoid architecture that prevents their later addition.

- Chrome extension support.
- Chrome Web Store compatibility layer.
- Advanced extension permission management.
- Cross-device synchronization.
- Cloud browser profiles.
- Cloud task history.
- Voice commands.
- Speech-to-text.
- Text-to-speech.
- Browser workflow recording.
- Reusable automation templates.
- Scheduled browser tasks.
- More advanced local memory.
- Additional operating systems.
- Custom Chromium fork.
- Advanced developer tools.
- Browser automation marketplace.

Keep extension integration behind a future ExtensionManager interface.

Do not simulate Chrome extension compatibility in the first version.

---

# 24. DEVELOPMENT OPERATING RULES

You must follow these rules while working on the project.

## Rule 1: Work in actual implementation

Do not return only an architecture document.

Create real files and working code.

## Rule 2: Work phase by phase

Complete a phase, run its tests, fix failures and then proceed.

## Rule 3: No fake features

Do not create buttons that do nothing.

Do not return hardcoded AI responses.

Do not use fake browser actions.

Do not simulate successful automation.

If a feature is not implemented, clearly label it as unavailable.

## Rule 4: Maintain project documentation

Update:

- README.md
- ARCHITECTURE.md
- API.md
- DEVELOPMENT.md
- SECURITY.md

## Rule 5: Maintain dependency integrity

- Pin dependencies.
- Maintain lockfiles.
- Avoid unused packages.
- Check security advisories.
- Document dependency upgrades.

## Rule 6: Maintain code quality

Use:

- Type hints.
- Typed IPC contracts.
- Pydantic validation.
- Structured logging.
- Error boundaries.
- Modular services.
- Dependency injection where appropriate.
- Unit and integration tests.

## Rule 7: Do not overwrite existing work

Inspect repository contents before modifying files.

Preserve valid existing files and configuration.

## Rule 8: Do not conceal incomplete work

At the end of every phase, report:

- What was implemented.
- Files created.
- Files modified.
- Commands executed.
- Tests passed.
- Tests failed.
- Outstanding limitations.
- Next phase.

## Rule 9: Never ask me to manually implement code that you can implement yourself

Make reasonable technical decisions and document them.

Only request external credentials or user actions when genuinely required.

Never initiate real external financial transactions, messages or other sensitive operations during testing.

## Rule 10: Prioritize a running product

The ultimate objective is a working installable browser, not just an impressive folder structure.

---

# 25. FINAL DELIVERABLES

The completed project must include:

1. Complete Windows desktop browser.
2. Functional Chromium browsing.
3. Multi-tab browser manager.
4. Premium React browser interface.
5. Working AI assistant sidebar.
6. NVIDIA NIM integration.
7. Additional AI provider adapter.
8. Model selection and configuration.
9. Python FastAPI backend.
10. Secure Electron/Python communication.
11. DOM-based automation.
12. Screenshot-based automation.
13. Browser agent.
14. Supervisor and task planner.
15. Multi-tab research.
16. Search provider abstraction.
17. Source citations.
18. Local SQLite database.
19. Conversation history.
20. Local task history.
21. Approval and safety system.
22. Settings and first-run wizard.
23. Automated tests.
24. Security documentation.
25. Windows NSIS installer.
26. Installation and user documentation.

---

# 26. DEFINITION OF DONE

The application is not complete merely because it launches.

It must successfully demonstrate all of these scenarios:

TEST 1 — Normal browsing

Open several websites, navigate between them and use browser history.

TEST 2 — AI webpage understanding

Open a webpage and ask the AI to summarize it accurately.

TEST 3 — Research

Search for a topic, open several sources and generate a cited comparison.

TEST 4 — Multi-tab understanding

Open three websites and ask the assistant to compare their content.

TEST 5 — DOM automation

Ask the agent to find an element, click it and verify the resulting state.

TEST 6 — Form automation

Use a controlled test website to fill a form and display the completed draft without automatically submitting sensitive information.

TEST 7 — Vision automation

Ask the agent to identify and interact with a visual control that cannot reliably be identified using DOM inspection.

TEST 8 — Autonomous multi-step task

Ask the agent to gather information from multiple websites, organize the data and generate a CSV file.

TEST 9 — Permission system

Confirm that sensitive actions are paused until explicit authorization is obtained.

TEST 10 — Recovery

Disconnect the AI provider, restart the backend and confirm that normal browser functionality remains available.

TEST 11 — Security

Confirm that a malicious webpage cannot access Electron APIs, steal provider keys or override the application's trusted instructions.

TEST 12 — Windows installation

Install the packaged application on a clean supported Windows environment, launch it, browse and uninstall it successfully.

All tests must have documented results.

---

# 27. START THE PROJECT NOW

Begin with Phase 0.

First inspect the repository and the installed development environment.

Then create the foundation.

Your first working milestone must demonstrate:

- Electron application opens.
- Browser toolbar renders.
- Tab system works.
- Real Chromium webpage appears in a WebContentsView.
- Python FastAPI backend starts.
- Electron and Python communicate successfully.
- A page can be inspected through the controlled CDP bridge.
- A screenshot can be captured.
- No remote debugging port is publicly exposed.

After Phase 0 passes, continue with Phase 1 and the remaining phases in order.

Do not stop after generating files.

Run the application, inspect actual behavior, execute tests, fix errors and keep moving toward the complete product.

**FINAL PRODUCT VISION**

Build a premium Windows AI browser where a person can browse normally, ask questions about any webpage, research information across multiple websites and delegate real browser tasks to an intelligent AI agent.

It should combine the strengths of an AI research assistant and an autonomous browser automation system in one reliable, secure and locally controlled desktop application.

The finished result must be a functional software product, not a prototype consisting only of UI screens.
