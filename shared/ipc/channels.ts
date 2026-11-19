export const IPC_CHANNELS = {
  // Tabs
  TAB_CREATE: 'tab:create',
  TAB_CLOSE: 'tab:close',
  TAB_SWITCH: 'tab:switch',
  TAB_STATE_CHANGED: 'tab:state-changed',
  TABS_GET: 'tabs:get',

  // Navigation
  NAV_NAVIGATE: 'nav:navigate',
  NAV_BACK: 'nav:back',
  NAV_FORWARD: 'nav:forward',
  NAV_RELOAD: 'nav:reload',
  NAV_STOP: 'nav:stop',

  // Panel toggles & Layout
  PANEL_TOGGLE_ASSISTANT: 'panel:toggle-assistant',
  PANEL_TOGGLE_SIDEBAR: 'panel:toggle-sidebar',
  GET_INITIAL_STATE: 'app:get-initial-state',

  // Browser Actions & CDP
  CAPTURE_PAGE: 'browser:capture-page',
  INSPECT_PAGE: 'browser:inspect-page',

  // Backend state
  BACKEND_STATUS: 'backend:status',

  // Assistant & Chat
  SEND_CHAT_MESSAGE: 'chat:send-message',
  CHAT_STREAM_CHUNK: 'chat:stream-chunk'
} as const;

export type IpcChannel = typeof IPC_CHANNELS[keyof typeof IPC_CHANNELS];
