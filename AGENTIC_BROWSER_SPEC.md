# MASTER IMPLEMENTATION PROMPT: UPGRADE EXISTING BROWSER INTO A COMPLETE AGENTIC AI BROWSER

## ROLE

Act as a principal software architect, senior Electron/Chromium engineer, Python FastAPI developer, AI/ML engineer, browser automation specialist, UI/UX designer, and application security engineer.

Your mission is to transform my ALREADY BUILT browser application into a powerful, production-grade, agentic AI browser.

This is an existing project. You must upgrade and extend the existing codebase.

**DO NOT rebuild the application from scratch. DO NOT replace the existing browser architecture unnecessarily. DO NOT remove working functionality.**

Your first responsibility is to understand the current project, its architecture, code, dependencies, UI, APIs, and existing AI integration.

Then implement the new capabilities incrementally while preserving everything that already works.

---

# 1. EXISTING PROJECT CONFIGURATION

Use these architectural decisions as the target configuration, adapting them to the actual implementation where necessary.

- Platform: Windows
- Desktop framework: Electron
- Browser engine: Existing Chromium implementation
- Backend: Python FastAPI
- AI architecture: Multi-agent system
- AI provider: NVIDIA NIM integration
- Automation: Browser automation AND Windows desktop automation
- Data storage: Local-first
- Synchronization: No mandatory cloud synchronization
- Browser extension ecosystem: Future expansion
- Product direction: Personal AI browser + advanced automation platform
- UI: Modern desktop application
- Architecture: Modular, extensible, secure and maintainable

Do not assume that the existing project has exactly this architecture. Inspect the actual codebase and adapt without breaking the working implementation.

# 2. FIRST STEP: COMPLETE EXISTING PROJECT AUDIT

Before making code changes, inspect:

1. Complete project directory and file structure.
2. Electron main process.
3. Electron preload scripts.
4. Renderer process.
5. Chromium or browser implementation.
6. Tab and navigation management.
7. Current browser UI and components.
8. Current FastAPI backend.
9. Existing API endpoints.
10. NVIDIA NIM integration.
11. Existing AI models and prompts.
12. Existing automation implementation.
13. Browser control and CDP integration.
14. Local database and storage.
15. Existing settings and configuration.
16. Existing authentication and security mechanisms.
17. Logging and error-handling systems.
18. Existing tests and build configuration.

Create an internal feature-to-codebase mapping.

Classify every proposed capability as:

- Already implemented.
- Partially implemented.
- Missing.
- Requires architectural modification.
- Future integration.

Do not duplicate features that already work.

Do not replace existing libraries simply because another library is available.

Before editing, identify possible breaking changes and preserve the existing working implementation.

# 3. PRODUCT GOAL

Convert the browser into a complete AI-powered agentic environment.

The user should be able to enter a simple natural-language instruction, and the system should be able to:

1. Understand the objective.
2. Understand the current browser context.
3. Create an execution plan.
4. Select appropriate AI agents.
5. Execute browser actions.
6. Read and understand webpage content.
7. Navigate multiple websites.
8. Extract and organize information.
9. Perform permitted repetitive tasks.
10. Handle errors and unexpected website changes.
11. Verify the results.
12. Request approval for sensitive actions.
13. Generate reports.
14. Save reusable workflows.
15. Resume interrupted tasks.
16. Explain what it completed.

The application must be a real working automation product, not just an AI chat interface.

# 4. FEATURE MODULES TO IMPLEMENT

Implement the following capabilities by integrating them into the existing application.

## MODULE A: ADVANCED BROWSER FOUNDATION

Improve the existing browser without removing its current functionality.

Features:

- Advanced tab manager.
- Multiple browser windows.
- Tab groups.
- Pinned tabs.
- Duplicate tabs.
- Tab search.
- Browser profiles.
- Session restoration.
- Browsing history.
- Bookmark manager.
- Download manager.
- Password manager integration.
- Autofill.
- Form management.
- Search engine management.
- Website permissions.
- Cookie management.
- Site-specific settings.
- Browser themes.
- Light and dark modes.
- Full-page screenshots.
- PDF viewing.
- Print and save as PDF.
- Find on page.
- Translation.
- Reader mode.
- Keyboard shortcuts.
- Developer tools.
- Network inspector.
- Browser logs.
- Crash recovery.
- Persistent sessions.

Maintain compatibility with the current browser navigation and tab architecture.

## MODULE B: UNIFIED AI ASSISTANT

Build an intelligent AI sidebar integrated with the current browser.

Features:

- AI conversation interface.
- Ask about the active webpage.
- Page summarization.
- Article summarization.
- PDF summarization.
- Video summarization where supported.
- Selected-text explanation.
- Text rewriting.
- Translation.
- Grammar correction.
- AI writing assistant.
- Research assistant.
- Product comparison.
- Information extraction.
- Table extraction.
- Context-aware conversations.
- Follow-up questions.
- Chat history.
- Voice input.
- Text-to-speech.
- Screenshot analysis.
- Image understanding.
- Source citations.
- AI search.

The AI assistant should understand the current tab and only access other browser contexts when the user or an authorized task requires them.

## MODULE C: AGENTIC AI ORCHESTRATOR

Implement a proper autonomous agent orchestration system.

Create a central Orchestrator Agent responsible for:

- Understanding user instructions.
- Breaking goals into subtasks.
- Generating execution plans.
- Assigning tasks to specialized agents.
- Selecting appropriate tools.
- Managing task state.
- Tracking execution progress.
- Handling agent failures.
- Verifying task completion.
- Asking for user approval.
- Generating final reports.

Implement the following specialized agents where appropriate:

1. Planner Agent.
2. Research Agent.
3. Browser Agent.
4. DOM Agent.
5. Vision Agent.
6. Automation Agent.
7. Data Extraction Agent.
8. Verification Agent.
9. Memory Agent.
10. Security Agent.
11. PDF Agent.
12. Shopping Agent.
13. Email Agent.
14. Coding Agent.
15. File Management Agent.
16. Recovery Agent.
17. Report Generation Agent.

Requirements:

- Agent-to-agent communication.
- Shared task context.
- Structured agent messages.
- Agent delegation.
- Task queues.
- Parallel execution where safe.
- Agent execution limits.
- Model routing.
- Error recovery.
- Agent status reporting.
- Cancellation and interruption.
- Independent result verification.
- Task execution traces.

Do not create artificial agents that are merely separate names pointing to the same unstructured prompt. Give each agent a defined responsibility, tools, input schema, output schema and execution restrictions.

## MODULE D: ADVANCED BROWSER AUTOMATION ENGINE

This is one of the most important components.

Implement a unified browser automation system using appropriate existing browser-control capabilities.

Support:

- DOM-based automation.
- Accessibility-based automation.
- Visual automation.
- Keyboard interaction.
- Mouse interaction.
- Scrolling.
- Clicking.
- Typing.
- Selecting dropdowns.
- Checking and unchecking boxes.
- Opening and closing tabs.
- Navigating websites.
- Working with dynamic content.
- Detecting interactive elements.
- Reading webpage content.
- Working with supported frames.
- Uploading files.
- Downloading files.
- Interacting with dialogs.
- Detecting page loading.
- Handling navigation changes.
- Waiting for dynamic elements.
- Recovering from failed actions.

Build a unified action interface.

Suggested action categories:

- browser.navigate
- browser.click
- browser.type
- browser.scroll
- browser.select
- browser.check
- browser.get_page
- browser.get_text
- browser.get_links
- browser.get_elements
- browser.take_screenshot
- browser.switch_tab
- browser.open_tab
- browser.close_tab
- browser.download
- browser.upload
- browser.wait
- browser.go_back
- browser.go_forward

Use structured arguments and validated outputs.

Do not let an AI model directly execute unrestricted browser or operating-system commands.

All actions must go through a controlled tool registry with permission checks.

Implement multiple automation strategies:

1. DOM-first interaction.
2. Accessibility-tree interaction.
3. Visual interaction when DOM access is insufficient.
4. Keyboard and mouse fallback.
5. Post-action verification.

Use appropriate existing technologies rather than introducing unnecessary dependencies.

## MODULE E: AI FORM AUTOMATION

Implement advanced form automation.

Features:

- Automatically detect forms.
- Identify field labels.
- Understand input types.
- Map user data to form fields.
- Fill text fields.
- Select dropdown options.
- Select dates.
- Upload files.
- Handle multi-step forms.
- Detect required fields.
- Detect validation errors.
- Correct incomplete entries.
- Preview completed forms.
- Capture submission confirmations.
- Reuse user-approved form profiles.
- Save reusable form mappings.

Before submitting a form that changes external records, request explicit user approval.

Do not bypass CAPTCHA, authentication or website access controls.

## MODULE F: WORKFLOW RECORDER AND BUILDER

Build a complete workflow automation system.

### Workflow Recorder

Allow users to record:

- Clicks.
- Text entry.
- Navigation.
- Dropdown selection.
- Keyboard interactions.
- Form interactions.
- Browser actions.
- Supported desktop actions.

Store meaningful selectors and action context instead of relying exclusively on screen coordinates.

Allow users to:

- Stop recording.
- Pause recording.
- Resume recording.
- Edit recorded actions.
- Delete actions.
- Reorder steps.
- Add descriptions.
- Add variables.
- Replay recordings.
- Save reusable workflows.
- Import and export workflows.

### Visual Workflow Builder

Create a drag-and-drop workflow editor.

Support workflow nodes:

- Start.
- Navigate.
- Click.
- Type.
- Scroll.
- Wait.
- Extract data.
- Screenshot.
- Condition.
- Loop.
- For each.
- API request.
- File operation.
- AI reasoning.
- Data transformation.
- Verification.
- Approval.
- End.

Support:

- Connecting nodes.
- Editing node configurations.
- Conditional branches.
- Loops.
- Variables.
- Workflow validation.
- Workflow execution.
- Step-by-step debugging.
- Execution logs.
- Save and load.
- JSON import/export.
- Workflow templates.
- Workflow versioning.

Make the workflow builder fully functional. Do not deliver a decorative diagram without an execution engine.

## MODULE G: WEB RESEARCH ENGINE

Implement deep research capabilities.

Features:

- Natural-language research.
- Multi-website research.
- Multi-source information collection.
- Source tracking.
- Source citations.
- Research notes.
- Fact comparison.
- Contradiction detection.
- Information verification.
- Topic discovery.
- Research history.
- Structured reports.
- Timeline generation.
- Table extraction.
- Entity extraction.
- Research export.
- Automatic references.

The Research Agent must distinguish between verified information, inferred information and unresolved information.

Maintain source URLs and supporting excerpts for extracted claims.

## MODULE H: ADVANCED DATA EXTRACTION

Implement structured webpage data extraction.

Support:

- Text extraction.
- Table extraction.
- Product information extraction.
- Publicly available business information extraction.
- Links.
- Metadata.
- Images where permitted.
- Pagination.
- Multiple-page extraction.
- Structured records.
- Duplicate detection.
- Data normalization.
- Data validation.
- JSON export.
- CSV export.
- Excel export.
- PDF reports.
- Local storage.
- Google Sheets integration as an optional future connector.
- Google Drive integration as an optional future connector.

Build a reusable extraction configuration system.

Respect website terms, applicable laws, privacy and access restrictions. Do not implement security or access-control bypasses.

## MODULE I: WINDOWS DESKTOP AUTOMATION

Extend the product beyond ordinary browser automation.

Create a separate permission-controlled Windows automation service.

Features:

- Screen capture.
- Screen understanding.
- Mouse interaction.
- Keyboard interaction.
- Window detection.
- Window switching.
- Application launching.
- File and folder selection.
- File management.
- Clipboard interaction with permission.
- Drag and drop.
- Multi-monitor support.
- Desktop workflow recording.
- Desktop workflow replay.
- Action history.
- Emergency stop.

Keep desktop automation isolated from the Electron renderer and normal website execution.

Every operation must be validated and authorized.

Never execute unrestricted shell commands generated by an AI model.

## MODULE J: MEMORY SYSTEM

Implement a local-first memory system.

Memory categories:

1. Short-term conversation memory.
2. Current task memory.
3. Long-term user preferences.
4. Workflow memory.
5. Research memory.
6. Website-specific task context.

Features:

- Save approved user preferences.
- Retrieve relevant memory.
- Semantic memory search.
- Memory summarization.
- Memory editing.
- Memory deletion.
- Memory expiration.
- Memory inspection.
- Task-specific memory isolation.
- Profile-specific memory.

Use a local database and an optional local vector index if beneficial.

Never store passwords, authentication tokens or sensitive personal data in ordinary AI memory.

## MODULE K: PDF AND DOCUMENT INTELLIGENCE

Implement:

- PDF reading.
- PDF question answering.
- PDF summarization.
- OCR for scanned PDFs.
- Table extraction.
- Multiple PDF comparison.
- Document search.
- Document classification.
- Data extraction.
- Document translation.
- Citation tracking.
- Report generation.
- PDF export.
- Downloaded-document organization.

Include document-page references when answering questions about PDFs.

## MODULE L: SHOPPING AND COMPARISON ASSISTANT

Implement:

- Product discovery.
- Product specification extraction.
- Product comparison.
- Price comparison.
- Review summarization.
- Alternative product discovery.
- Budget-based recommendations.
- Wishlist.
- Price monitoring.
- Price history where available.
- Deal notifications.
- Comparison report generation.

Do not fabricate prices, ratings, discounts or reviews.

Require confirmation before purchases or checkout actions. Never perform payment actions autonomously.

## MODULE M: EMAIL AND PRODUCTIVITY INTEGRATION

Create extensible connectors for supported services.

Features:

- Email search.
- Email summarization.
- Email reply drafting.
- Email classification.
- Task extraction.
- Deadline identification.
- Calendar event drafting.
- Meeting summaries.
- Attachment extraction.
- Document summarization.
- Follow-up drafting.
- Productivity task generation.

Use official APIs or explicitly authorized integrations where possible.

Sending emails, creating events and modifying external records require user authorization.

## MODULE N: AI VOICE AND MULTIMODAL SYSTEM

Implement:

- Speech-to-text.
- Text-to-speech.
- Voice commands.
- Voice conversation.
- Voice-based browser control.
- Voice task status.
- Screenshot understanding.
- Image analysis.
- OCR.
- Video summarization where supported.
- Audio summarization where supported.
- Multilingual interaction.

Allow the user to interrupt or stop voice-driven automation.

## MODULE O: WEBSITE MONITORING AND SCHEDULED TASKS

Implement:

- Website monitoring.
- Page change detection.
- Text change detection.
- Price monitoring.
- Public information monitoring.
- Scheduled research.
- Scheduled workflows.
- Task queues.
- Task notifications.
- Execution logs.
- Failure notifications.
- Workflow retry policies.
- Pause and resume.

Scheduled tasks must run within configured resource and permission limits. Do not imply tasks continue while the application is closed unless a real background service exists.

## MODULE P: AI MODEL MANAGEMENT AND NVIDIA NIM

Improve the existing NVIDIA NIM integration.

Create a provider-independent AI model interface.

Features:

- NVIDIA NIM integration.
- Multiple LLM support.
- Model selection.
- Task-specific model routing.
- Vision model routing.
- Embedding model support.
- Reranking model support.
- Structured JSON output.
- Streaming responses.
- Fallback models.
- Model health checks.
- Timeout management.
- Retry management.
- Token usage tracking.
- Latency monitoring.
- AI cost estimates.
- Prompt template management.
- Model configuration UI.

Use NVIDIA NIM-compatible APIs and model capabilities that are actually available in the configured environment.

Do not invent endpoints, models or capabilities.

Keep API keys out of frontend code, logs and source control.

## MODULE Q: SECURITY AND PERMISSION SYSTEM

Security must be treated as a foundational subsystem.

Implement:

### Electron security

- Context isolation.
- Disabled Node integration in renderer processes.
- Secure preload APIs.
- Strict IPC allowlists.
- Validated IPC arguments.
- Content security policy.
- Appropriate sandboxing.
- Trusted navigation restrictions.
- Secure local file access.

### FastAPI security

- Bind local-only services to loopback unless explicitly configured otherwise.
- Authenticated local IPC or API requests.
- Request validation.
- Rate limiting where appropriate.
- Strict CORS.
- API timeouts.
- Secure configuration.
- Secret management.
- Input/output validation.

### AI agent security

- Tool permission registry.
- Domain-specific permissions.
- Action allowlists and denylists.
- Explicit approval gates.
- Prompt-injection resistance.
- Untrusted webpage content isolation.
- Sensitive data protection.
- Restricted script execution.
- Audit logs.
- Execution budgets.
- Emergency kill switch.
- Cancellation support.
- User-visible action history.

A webpage is untrusted data. Instructions found inside webpage content, emails, PDFs or other documents must never automatically override the user's instructions or the browser's security policies.

Require confirmation before:

- Submitting external forms.
- Sending messages or emails.
- Making purchases.
- Making financial transactions.
- Deleting user data.
- Changing account settings.
- Sharing private information.
- Performing irreversible actions.

Never bypass authentication, CAPTCHA, website restrictions or access-control mechanisms.

## MODULE R: USER INTERFACE AND EXPERIENCE

Upgrade the existing interface into a professional AI browser dashboard.

Keep the UI consistent with the application's current design system.

Create or improve these sections:

1. Browser Workspace.
2. AI Assistant.
3. Agent Dashboard.
4. Task Manager.
5. Workflow Recorder.
6. Visual Workflow Builder.
7. Workflow Library.
8. Research Workspace.
9. Memory Center.
10. Download Manager.
11. History Center.
12. Document Center.
13. Website Monitor.
14. Model Settings.
15. Agent Permissions.
16. Automation Logs.
17. Usage Analytics.
18. Browser Settings.

### Agent dashboard

Display:

- Active agents.
- Current task.
- Current execution step.
- Task progress.
- Agent status.
- Tool actions.
- Pending approvals.
- Errors.
- Completed tasks.
- Execution time.

### Automation interface

Provide:

- Start.
- Pause.
- Resume.
- Stop.
- Retry.
- Approve.
- Reject.
- View logs.
- View screenshots.
- View execution steps.

Make the UI responsive within the desktop application.

Avoid overcrowded interfaces. Use reusable components and maintain a consistent visual language.

# 5. TECHNICAL ARCHITECTURE

Adapt the actual project to a modular architecture.

Suggested logical backend structure:

backend/
    app/
        main.py
        api/
        core/
        config/
        agents/
            orchestrator/
            planner/
            research/
            browser/
            dom/
            vision/
            automation/
            extraction/
            verification/
            memory/
            security/
        automation/
            browser/
            desktop/
            actions/
            selectors/
            execution/
            recorder/
            workflow_engine/
        ai/
            providers/
            nvidia_nim/
            model_router/
            prompts/
            embeddings/
        tools/
            browser_tools/
            document_tools/
            file_tools/
            research_tools/
            productivity_tools/
        memory/
        database/
        integrations/
        scheduler/
        monitoring/
        logging/
        schemas/
        tests/

electron/
    main/
    preload/
    renderer/
        components/
        pages/
        layouts/
        hooks/
        services/
        stores/
        styles/
    browser/
    ipc/
    services/
    assets/

workflows/
    templates/
    user_workflows/

tests/
    backend/
    frontend/
    integration/
    automation/
    security/

Treat this as a suggested organization, not a requirement to move every existing file. Preserve the existing structure where it is already clean and functional.

# 6. DATABASE AND LOCAL STORAGE

Use a local-first architecture.

Evaluate the existing database before selecting another one.

Suggested entities:

- BrowserProfile.
- BrowserSession.
- BrowserTab.
- Bookmark.
- BrowsingHistory.
- DownloadRecord.
- Conversation.
- Message.
- Agent.
- AgentRun.
- Task.
- TaskStep.
- ToolExecution.
- Workflow.
- WorkflowVersion.
- WorkflowNode.
- WorkflowExecution.
- Memory.
- ResearchSession.
- ResearchSource.
- ExtractedRecord.
- WebsiteMonitor.
- ScheduledJob.
- ApprovalRequest.
- AuditLog.
- ModelConfiguration.

Store structured information in the local database and large files in organized local directories.

Use migrations and avoid destructive database changes.

Keep credentials in an appropriate operating-system secure storage facility.

# 7. API DESIGN

Implement typed, documented API endpoints according to the existing backend conventions.

Suggested API groups:

/api/assistant
/api/agents
/api/tasks
/api/browser
/api/automation
/api/workflows
/api/recorder
/api/research
/api/extraction
/api/memory
/api/documents
/api/monitoring
/api/scheduler
/api/models
/api/permissions
/api/logs
/api/settings

Provide suitable endpoints for:

- Creating tasks.
- Getting task status.
- Cancelling tasks.
- Pausing tasks.
- Resuming tasks.
- Approving actions.
- Rejecting actions.
- Executing browser tools.
- Running workflows.
- Saving workflows.
- Retrieving execution history.
- Managing model configurations.

Use WebSockets or the existing real-time communication mechanism for task progress and streaming events.

Validate every API request and response.

Do not expose sensitive internal tool functions directly to the frontend.

# 8. TASK EXECUTION ENGINE

Implement a reliable task lifecycle.

Suggested lifecycle:

CREATED
    ↓
UNDERSTANDING
    ↓
PLANNING
    ↓
AWAITING_APPROVAL (when required)
    ↓
EXECUTING
    ↓
VERIFYING
    ↓
COMPLETED

Additional states:

PAUSED
CANCELLED
FAILED
NEEDS_USER_INPUT
NEEDS_RECOVERY

Every task should have:

- Unique task ID.
- User instruction.
- Execution plan.
- Agent assignments.
- Current step.
- Execution logs.
- Tool call records.
- Approval requirements.
- Result data.
- Failure information.
- Retry information.
- Start and completion timestamps.

Implement checkpointing so recoverable tasks can resume without blindly repeating completed external actions.

Before retrying an external action, determine whether that action already succeeded.

# 9. IMPLEMENTATION STRATEGY

Do not attempt to add the entire feature inventory in one uncontrolled code-generation operation.

Implement in production-quality phases.

### PHASE 1: FOUNDATION AND INTEGRATION

- Audit the project.
- Preserve existing functionality.
- Improve application architecture.
- Build or improve the AI sidebar.
- Improve NVIDIA NIM integration.
- Establish the unified tool registry.
- Establish secure browser control.
- Establish task and event architecture.
- Add tests.

### PHASE 2: AGENTIC BROWSER

- Orchestrator.
- Planner.
- Browser Agent.
- DOM Agent.
- Research Agent.
- Verification Agent.
- Task lifecycle.
- Multi-step execution.
- Approval interface.
- Cancellation and recovery.

### PHASE 3: AUTOMATION PLATFORM

- Browser automation tools.
- Form automation.
- Workflow recorder.
- Workflow storage.
- Visual workflow builder.
- Workflow execution engine.
- Import/export.
- Debugging and logging.

### PHASE 4: RESEARCH AND DOCUMENT INTELLIGENCE

- Deep research.
- Source citations.
- Data extraction.
- PDF intelligence.
- Document comparison.
- Research reports.
- Excel, CSV and JSON exports.

### PHASE 5: ADVANCED AI SYSTEMS

- Agent specialization.
- Model routing.
- Local memory.
- Voice interaction.
- Image understanding.
- Website monitoring.
- Scheduled workflows.
- Product comparison.
- Productivity integrations.

### PHASE 6: WINDOWS DESKTOP AUTOMATION

- Permission-controlled desktop service.
- Screen understanding.
- Mouse and keyboard.
- Application switching.
- File operations.
- Desktop workflow recording.
- Desktop workflow playback.

### PHASE 7: HARDENING AND PRODUCTION RELEASE

- Security auditing.
- Performance optimization.
- Regression testing.
- Error recovery testing.
- Installer improvements.
- Logging.
- Documentation.
- Release validation.

# 10. ENGINEERING RULES

These rules are mandatory.

1. Inspect existing code before changing anything.
2. Never remove working features.
3. Never rewrite the whole project unnecessarily.
4. Reuse existing components and services.
5. Keep frontend and backend responsibilities separate.
6. Use typed interfaces and validated schemas.
7. Use asynchronous execution for long-running tasks.
8. Do not block the Electron UI during AI inference or automation.
9. Use controlled queues for concurrent tasks.
10. Implement timeouts and cancellation.
11. Implement meaningful logging.
12. Avoid hardcoded API keys and credentials.
13. Avoid hardcoded machine-specific paths.
14. Avoid duplicate dependencies.
15. Avoid placeholder functionality presented as complete.
16. Avoid fake AI responses.
17. Avoid mock automation in production paths.
18. Do not silently swallow exceptions.
19. Maintain database migrations.
20. Maintain backward compatibility where practical.
21. Add tests for every major feature.
22. Keep modules independent and replaceable.
23. Document significant architectural decisions.
24. Do not mark a feature complete until it actually works.

For every newly introduced dependency, explain why it is necessary and check compatibility with the existing project.

# 11. TESTING REQUIREMENTS

Implement automated testing at multiple levels.

### Backend

- API tests.
- Agent tests.
- Orchestrator tests.
- Tool registry tests.
- Permission tests.
- Database tests.
- Memory tests.
- Model routing tests.
- Task lifecycle tests.

### Frontend

- Component tests.
- Navigation tests.
- AI sidebar tests.
- Task dashboard tests.
- Workflow builder tests.
- Approval interaction tests.

### Browser automation

- Navigation.
- Element detection.
- Clicking.
- Typing.
- Dropdown selection.
- Form filling.
- Screenshots.
- Dynamic pages.
- Tab switching.
- Error recovery.

### Security

- Unauthorized tool execution.
- Malicious page instructions.
- IPC access restrictions.
- API authentication.
- Sensitive information handling.
- Approval enforcement.
- Restricted file access.
- Cancellation enforcement.

### End-to-end scenarios

Test these complete user workflows:

TEST 1:
"Open three websites, research a topic, compare information and create a cited report."

TEST 2:
"Open a website, fill in a sample form, preview the information and ask me before submitting."

TEST 3:
"Record a browser workflow, save it and execute it again."

TEST 4:
"Extract information from several permitted pages and export it into Excel."

TEST 5:
"Read a local PDF, answer questions about it and prepare a summary."

TEST 6:
"Monitor a webpage and notify me when specified content changes."

TEST 7:
"Create a workflow using conditional logic and execute it."

TEST 8:
"Ask an agent to perform a task, pause execution, resume and then cancel it."

TEST 9:
"Encounter a failed browser action and recover without repeating an already completed external action."

TEST 10:
"Detect malicious instructions embedded in webpage content and refuse unauthorized actions."

Use local test websites and synthetic data where possible.

# 12. PERFORMANCE AND RELIABILITY

Optimize for:

- Fast browser startup.
- Low idle memory usage.
- Responsive Electron UI.
- Efficient browser action execution.
- Controlled concurrent agents.
- Efficient model calls.
- Streaming responses.
- Background processing.
- Database performance.
- Large document handling.
- Recovery from network failures.
- Graceful model-provider outages.
- Stable tab and session management.

Avoid sending entire webpages or unnecessary browser data to AI models. Use relevant content extraction, summarization and context limits.

# 13. REQUIRED DELIVERABLES

After implementing each phase, provide:

1. Files created.
2. Files modified.
3. Features implemented.
4. Existing features preserved.
5. Architecture changes.
6. New dependencies.
7. API endpoint documentation.
8. Database changes.
9. Security changes.
10. Tests added.
11. Test results.
12. Known limitations.
13. Instructions to run the application.
14. Instructions to configure NVIDIA NIM.
15. Next recommended implementation phase.

Maintain an implementation checklist with these statuses:

- COMPLETE.
- PARTIALLY COMPLETE.
- NOT IMPLEMENTED.
- BLOCKED.
- REQUIRES EXTERNAL CREDENTIALS.

Never report a feature as complete when it is only a UI mockup or placeholder.

# 14. FINAL INSTRUCTIONS

Start by auditing the existing repository.

Do not immediately begin rewriting code.

After the audit:

1. Present a concise architecture summary.
2. Present the existing-feature mapping.
3. Identify architectural problems and risks.
4. Create an implementation plan based on the actual repository.
5. Identify the first safe implementation batch.
6. Begin implementing the first batch immediately.

Continue with the implementation in small, testable, independently functional increments.

Do not stop after giving me a plan or architecture document. The objective is actual code implementation.

Work within the existing codebase, preserve existing functionality and run relevant tests after every meaningful change.

When a feature depends on external credentials, services or infrastructure, implement the integration interface and configuration UI, document the missing dependency and mark it appropriately instead of pretending it works.

**ULTIMATE OBJECTIVE:**

Transform my existing browser into a powerful, secure, modular, production-grade AGENTIC AI BROWSER powered by NVIDIA NIM, capable of intelligent web research, multi-agent collaboration, autonomous browser automation, visual interaction, workflow recording, workflow execution, advanced data extraction, document intelligence and permission-controlled Windows desktop automation.

The final product should function as an AI-powered browser AND an advanced automation platform.

Preserve the application I already built. Upgrade it intelligently. Do not destroy and rebuild it.
