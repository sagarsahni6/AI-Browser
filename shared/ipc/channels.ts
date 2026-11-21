export const IPC_CHANNELS = {
  // Tabs
  TAB_CREATE: 'tab:create',
  TAB_CLOSE: 'tab:close',
  TAB_SWITCH: 'tab:switch',
  TAB_STATE_CHANGED: 'tab:state-changed',
  TABS_GET: 'tabs:get',
  TAB_RESTORE_CLOSED: 'tab:restore-closed',
  TAB_DUPLICATE: 'tab:duplicate',
  TAB_SET_PINNED: 'tab:set-pinned',

  // Navigation
  NAV_NAVIGATE: 'nav:navigate',
  NAV_BACK: 'nav:back',
  NAV_FORWARD: 'nav:forward',
  NAV_RELOAD: 'nav:reload',
  NAV_STOP: 'nav:stop',

  // History
  HISTORY_GET: 'history:get',
  HISTORY_SEARCH: 'history:search',
  HISTORY_CLEAR: 'history:clear',
  HISTORY_ITEM_ADDED: 'history:item-added',

  // Bookmarks
  BOOKMARKS_GET: 'bookmarks:get',
  BOOKMARK_ADD: 'bookmarks:add',
  BOOKMARK_REMOVE: 'bookmarks:remove',
  BOOKMARK_IS_SAVED: 'bookmarks:is-saved',

  // Downloads
  DOWNLOADS_GET: 'downloads:get',
  DOWNLOAD_UPDATE: 'download:update',
  DOWNLOAD_OPEN_FILE: 'download:open-file',
  DOWNLOAD_OPEN_FOLDER: 'download:open-folder',

  // Panel toggles & Layout
  PANEL_TOGGLE_ASSISTANT: 'panel:toggle-assistant',
  PANEL_TOGGLE_SIDEBAR: 'panel:toggle-sidebar',
  PANEL_SET_ASSISTANT_OPEN: 'panel:set-assistant-open',
  PANEL_SET_SIDEBAR_OPEN: 'panel:set-sidebar-open',
  PANEL_ASSISTANT_STATE_CHANGED: 'panel:assistant-state-changed',
  PANEL_SIDEBAR_STATE_CHANGED: 'panel:sidebar-state-changed',
  GET_INITIAL_STATE: 'app:get-initial-state',

  // Browser Actions & CDP
  CAPTURE_PAGE: 'browser:capture-page',
  INSPECT_PAGE: 'browser:inspect-page',

  // COMET Self-Healing
  COMET_DISMISS_OVERLAY: 'comet:dismiss-overlay',
  COMET_LASER_INDICATOR: 'comet:laser-indicator',
  COMET_MODE_CHANGED: 'comet:mode-changed',

  // Backend state
  BACKEND_STATUS: 'backend:status',

  // Secrets & Settings
  SECRET_SET: 'secret:set',
  SECRET_GET: 'secret:get',

  // Assistant & Chat
  SEND_CHAT_MESSAGE: 'chat:send-message',
  CHAT_STREAM_CHUNK: 'chat:stream-chunk',
  CHAT_ACTION_UPDATE: 'chat:action-update',
  CHAT_INCOMING_PROMPT: 'chat:incoming-prompt',
  STOP_ASSISTANT: 'chat:stop',

  // Tasks & Multi-Agent Operations
  TASK_CREATE: 'task:create',
  TASKS_LIST: 'tasks:list',
  TASK_GET: 'task:get',
  TASK_CANCEL: 'task:cancel',
  TASK_PAUSE: 'task:pause',
  TASK_RESUME: 'task:resume',
  TASK_APPROVE: 'task:approve',
  TASK_REJECT: 'task:reject',
  TASK_STEP_UPDATED: 'task:step-updated',
  APPROVAL_REQUEST: 'approval:request',
  APPROVAL_RESPONSE: 'approval:response',

  // Research Collections
  COLLECTIONS_LIST: 'collections:list',
  COLLECTION_CREATE: 'collection:create',
  COLLECTION_DELETE: 'collection:delete',

  // Workflows & Automation Platform
  WORKFLOWS_LIST: 'workflows:list',
  WORKFLOW_GET: 'workflow:get',
  WORKFLOW_SAVE: 'workflow:save',
  WORKFLOW_DELETE: 'workflow:delete',
  WORKFLOW_EXECUTE: 'workflow:execute',
  WORKFLOW_EXPORT: 'workflow:export',
  WORKFLOW_IMPORT: 'workflow:import',
  WORKFLOW_RECORD_START: 'workflow:record-start',
  WORKFLOW_RECORD_STOP: 'workflow:record-stop',
  WORKFLOW_STEP_UPDATE: 'workflow:step-update',

  // Research & Document Intelligence + Advanced Data Extraction
  RESEARCH_SYNTHESIZE: 'research:synthesize',
  RESEARCH_LIST_REPORTS: 'research:list-reports',
  RESEARCH_GET_REPORT: 'research:get-report',
  RESEARCH_DELETE_REPORT: 'research:delete-report',
  DOCUMENTS_READ_PDF: 'documents:read-pdf',
  DOCUMENTS_SUMMARIZE_PDF: 'documents:summarize-pdf',
  DATA_EXTRACT_TABLE: 'data:extract-table',
  DATA_EXPORT: 'data:export',

  // Long-Term Memory & Context
  MEMORY_REMEMBER: 'memory:remember',
  MEMORY_RECALL: 'memory:recall',
  MEMORY_GET_ALL: 'memory:get-all',
  MEMORY_FORGET: 'memory:forget',

  // Website Monitoring & Scheduled Change Detection
  MONITORS_CREATE: 'monitors:create',
  MONITORS_LIST: 'monitors:list',
  MONITORS_CHECK_NOW: 'monitors:check-now',
  MONITORS_DELETE: 'monitors:delete',
  MONITOR_CHANGE_DETECTED: 'monitor:change-detected',

  // Windows Desktop Automation & Emergency Stop
  DESKTOP_CLICK: 'desktop:click',
  DESKTOP_TYPE: 'desktop:type',
  DESKTOP_HOTKEY: 'desktop:hotkey',
  DESKTOP_CAPTURE_SCREEN: 'desktop:capture-screen',
  DESKTOP_LAUNCH_APP: 'desktop:launch-app',
  DESKTOP_EMERGENCY_STOP: 'desktop:emergency-stop',
  DESKTOP_RESET_STOP: 'desktop:reset-stop',
  DESKTOP_GET_AUDIT_LOGS: 'desktop:get-audit-logs',
  DESKTOP_EMERGENCY_STOPPED: 'desktop:emergency-stopped',
} as const;

export type IpcChannel = typeof IPC_CHANNELS[keyof typeof IPC_CHANNELS];
