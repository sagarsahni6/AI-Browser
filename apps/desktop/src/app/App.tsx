import React, { useEffect, useState } from 'react';
import { ToolbarPanel } from '../panels/ToolbarPanel';
import { SidebarPanel } from '../panels/SidebarPanel';
import { AssistantPanel } from '../panels/AssistantPanel';
import { FirstRunWizard } from '../components/FirstRunWizard';
import { NewTabPage } from '../components/NewTabPage';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { useBrowserStore, applyTheme } from '../store/browser-store';
import { initLaserIndicator } from '../overlay/LaserIndicator';

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

      const unsubAction = window.electronAPI.onChatAction?.((action) => {
        useBrowserStore.getState().setActiveAction(action);
      });

      const unsubTaskStep = (window.electronAPI.onTaskStepUpdated || window.electronAPI.onTaskStepUpdate)?.((data: any) => {
        if (data?.status === 'approval_required') {
          useBrowserStore.getState().setActiveAction({
            action: data.action || data.tool_name || 'Action Requires Approval',
            parameters: {
              ...(data.parameters || {}),
              task_id: data.task_id,
              approval_id: data.approval_id
            },
            status: 'approval_required',
            result: data.reason || 'Action requires user confirmation',
            task_id: data.task_id,
            approval_id: data.approval_id
          } as any);
        } else if (data?.status === 'completed' || data?.status === 'failed' || data?.status === 'cancelled') {
          const currentAction = useBrowserStore.getState().activeAction as any;
          if (currentAction && (currentAction.task_id === data.task_id || currentAction.parameters?.task_id === data.task_id)) {
            useBrowserStore.getState().setActiveAction(null);
          }
        }
      });

      const unsubAssistant = window.electronAPI.onAssistantStateChanged?.((open) => {
        setAssistantOpen(open);
      });

      const unsubSidebar = window.electronAPI.onSidebarStateChanged?.((open) => {
        setSidebarOpen(open);
      });

      const unsubLaser = initLaserIndicator();

      return () => {
        unsubTabs();
        unsubBackend();
        unsubChat();
        unsubAction?.();
        unsubTaskStep?.();
        unsubAssistant?.();
        unsubSidebar?.();
        unsubLaser();
      };
    }
  }, [setTabs, setSidebarOpen, setAssistantOpen, setBackendStatus, appendChatChunk]);

  if (panel === 'toolbar') {
    return (
      <ErrorBoundary panelName="Toolbar">
        <ToolbarPanel />
      </ErrorBoundary>
    );
  }

  if (panel === 'welcome') {
    return (
      <ErrorBoundary panelName="Welcome Wizard">
        <FirstRunWizard
          onComplete={() => {
            localStorage.setItem('has_completed_onboarding', 'true');
            if (window.electronAPI?.navigate) {
              window.electronAPI.navigate('https://www.google.com');
            }
          }}
        />
      </ErrorBoundary>
    );
  }

  if (panel === 'sidebar') {
    return (
      <ErrorBoundary panelName="Sidebar">
        <SidebarPanel />
      </ErrorBoundary>
    );
  }

  if (panel === 'assistant') {
    return (
      <ErrorBoundary panelName="AI Assistant">
        <AssistantPanel />
      </ErrorBoundary>
    );
  }

  if (panel === 'newtab') {
    return (
      <ErrorBoundary panelName="New Tab Page">
        <NewTabPage />
      </ErrorBoundary>
    );
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
