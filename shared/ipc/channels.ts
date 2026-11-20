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
  GET_INITIAL_STATE: 'app:get-initial-state',

  // Browser Actions & CDP
  CAPTURE_PAGE: 'browser:capture-page',
  INSPECT_PAGE: 'browser:inspect-page',

  // Backend state
  BACKEND_STATUS: 'backend:status',

  // Secrets & Settings
  SECRET_SET: 'secret:set',
  SECRET_GET: 'secret:get',

  // Assistant & Chat
  SEND_CHAT_MESSAGE: 'chat:send-message',
  CHAT_STREAM_CHUNK: 'chat:stream-chunk',
  CHAT_ACTION_UPDATE: 'chat:action-update',
  STOP_ASSISTANT: 'chat:stop',

  // Tasks & Multi-Agent Operations
  TASK_CREATE: 'task:create',
  TASKS_LIST: 'tasks:list',
  TASK_GET: 'task:get',
  TASK_CANCEL: 'task:cancel',
  TASK_APPROVE: 'task:approve',
  TASK_REJECT: 'task:reject',

  // Research Collections
  COLLECTIONS_LIST: 'collections:list',
  COLLECTION_CREATE: 'collection:create',
  COLLECTION_DELETE: 'collection:delete',
} as const;

export type IpcChannel = typeof IPC_CHANNELS[keyof typeof IPC_CHANNELS];
