import React, { useEffect, useState } from 'react';
import { ToolbarPanel } from '../panels/ToolbarPanel';
import { SidebarPanel } from '../panels/SidebarPanel';
import { AssistantPanel } from '../panels/AssistantPanel';
import { FirstRunWizard } from '../components/FirstRunWizard';
import { useBrowserStore, applyTheme } from '../store/browser-store';

export const App: React.FC = () => {
  const [showWizard, setShowWizard] = useState(false);
  const {
    theme,
    setTabs,
    setSidebarOpen,
    setAssistantOpen,
    setBackendStatus,
    appendChatChunk
  } = useBrowserStore();

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => {
    const hasCompleted = localStorage.getItem('has_completed_onboarding');
    if (!hasCompleted && window.location.search.includes('panel=toolbar')) {
      setShowWizard(true);
    }
  }, []);

  const searchParams = new URLSearchParams(window.location.search);
  const panel = searchParams.get('panel');

  useEffect(() => {
    if (window.electronAPI) {
      window.electronAPI.getInitialState().then(state => {
        if (state) {
          setTabs(state.tabs, state.activeTabId);
          setSidebarOpen(state.sidebarOpen);
          setAssistantOpen(state.assistantOpen);
          setBackendStatus(state.backendStatus);
        }
      }).catch(console.error);

      const unsubTabs = window.electronAPI.onTabsUpdated((tabs, activeTabId) => {
        setTabs(tabs, activeTabId);
      });

      const unsubBackend = window.electronAPI.onBackendStatus((status) => {
        setBackendStatus(status);
      });

      const unsubChat = window.electronAPI.onChatStream((chunk) => {
        appendChatChunk(chunk);
      });

      return () => {
        unsubTabs();
        unsubBackend();
        unsubChat();
      };
    }
  }, [setTabs, setSidebarOpen, setAssistantOpen, setBackendStatus, appendChatChunk]);

  if (panel === 'toolbar') {
    return <ToolbarPanel />;
  }

  if (panel === 'welcome') {
    return (
      <FirstRunWizard
        onComplete={() => {
          localStorage.setItem('has_completed_onboarding', 'true');
          if (window.electronAPI?.navigate) {
            window.electronAPI.navigate('https://www.google.com');
          }
        }}
      />
    );
  }

  if (panel === 'sidebar') {
    return <SidebarPanel />;
  }

  if (panel === 'assistant') {
    return <AssistantPanel />;
  }

  // Fallback standalone preview (e.g. running vite standalone in standard browser)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100vw', height: '100vh' }}>
      <div style={{ height: '76px', width: '100%' }}>
        <ToolbarPanel />
      </div>
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div style={{ width: '220px', height: '100%' }}>
          <SidebarPanel />
        </div>
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
          WebContentsView Viewport Area
        </div>
        <div style={{ width: '360px', height: '100%' }}>
          <AssistantPanel />
        </div>
      </div>
    </div>
  );
};
