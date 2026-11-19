import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  RotateCw,
  Plus,
  X,
  Lock,
  Globe,
  Camera,
  Bot,
  PanelLeft,
  Search,
  Sparkles,
  ShieldCheck
} from 'lucide-react';
import { useBrowserStore } from '../store/browser-store';

export const ToolbarPanel: React.FC = () => {
  const {
    tabs,
    activeTabId,
    activeTab,
    sidebarOpen,
    assistantOpen,
    backendStatus,
    createTab,
    closeTab,
    switchTab,
    navigate,
    goBack,
    goForward,
    reload,
    toggleSidebar,
    toggleAssistant,
    capturePage,
    inspectPage
  } = useBrowserStore();

  const [addressInput, setAddressInput] = useState('');
  const [isInspecting, setIsInspecting] = useState(false);

  useEffect(() => {
    if (activeTab?.url) {
      setAddressInput(activeTab.url);
    }
  }, [activeTab?.url]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      let url = addressInput.trim();
      if (!url) return;
      if (!url.startsWith('http://') && !url.startsWith('https://') && !url.startsWith('about:')) {
        if (url.includes('.') && !url.includes(' ')) {
          url = 'https://' + url;
        } else {
          url = `https://www.google.com/search?q=${encodeURIComponent(url)}`;
        }
      }
      navigate(url);
    }
  };

  const handleCapture = async () => {
    try {
      await capturePage();
    } catch (err) {
      console.error('Capture error:', err);
    }
  };

  const handleInspect = async () => {
    setIsInspecting(true);
    try {
      await inspectPage();
    } catch (err) {
      console.error('Inspect error:', err);
    } finally {
      setIsInspecting(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      width: '100%',
      height: '100%',
      backgroundColor: 'var(--bg-primary)',
      borderBottom: '1px solid var(--border-subtle)',
      padding: '4px 8px 6px 8px',
      gap: '4px'
    }}>
      {/* Top Tabs Row */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '4px',
        overflowX: 'auto',
        minHeight: '32px'
      }}>
        {tabs.map(tab => {
          const isActive = tab.id === activeTabId;
          return (
            <div
              key={tab.id}
              onClick={() => switchTab(tab.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '4px 10px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: isActive ? 'var(--bg-secondary)' : 'transparent',
                border: isActive ? '1px solid var(--border-subtle)' : '1px solid transparent',
                cursor: 'pointer',
                maxWidth: '200px',
                minWidth: '110px',
                fontSize: '12px',
                color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                transition: 'background-color var(--transition-fast)'
              }}
            >
              {tab.isLoading ? (
                <RotateCw size={12} className="animate-spin" style={{ color: 'var(--accent-primary)' }} />
              ) : (
                <Globe size={12} style={{ opacity: 0.7 }} />
              )}
              <span style={{
                flex: 1,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap'
              }}>
                {tab.title || 'New Tab'}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  closeTab(tab.id);
                }}
                style={{
                  padding: '2px',
                  borderRadius: 'var(--radius-sm)',
                  opacity: 0.6
                }}
                title="Close Tab"
              >
                <X size={12} />
              </button>
            </div>
          );
        })}

        <button
          onClick={() => createTab()}
          className="icon-btn"
          style={{ width: '28px', height: '28px' }}
          title="New Tab"
        >
          <Plus size={14} />
        </button>

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Backend Status indicator */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '2px 8px',
          borderRadius: 'var(--radius-full)',
          backgroundColor: 'var(--bg-secondary)',
          fontSize: '11px',
          color: 'var(--text-secondary)'
        }}>
          <span style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: backendStatus.online ? 'var(--success)' : 'var(--error)'
          }} />
          <span>{backendStatus.online ? `Python :${backendStatus.port || 8000}` : 'Offline'}</span>
        </div>
      </div>

      {/* Bottom Navigation & Omnibox Row */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        width: '100%'
      }}>
        <button
          onClick={goBack}
          disabled={!activeTab?.canGoBack}
          className="icon-btn"
          title="Back"
        >
          <ArrowLeft size={16} />
        </button>
        <button
          onClick={goForward}
          disabled={!activeTab?.canGoForward}
          className="icon-btn"
          title="Forward"
        >
          <ArrowRight size={16} />
        </button>
        <button
          onClick={reload}
          className="icon-btn"
          title="Reload"
        >
          <RotateCw size={15} />
        </button>

        {/* Omnibox / Address Bar */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          flex: 1,
          backgroundColor: 'var(--bg-secondary)',
          borderRadius: 'var(--radius-md)',
          padding: '0 10px',
          height: '32px',
          border: '1px solid var(--border-subtle)',
          gap: '8px'
        }}>
          {addressInput.startsWith('https://') ? (
            <Lock size={13} style={{ color: 'var(--success)' }} />
          ) : (
            <Search size={13} style={{ color: 'var(--text-muted)' }} />
          )}
          <input
            type="text"
            value={addressInput}
            onChange={(e) => setAddressInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search or enter URL..."
            style={{
              flex: 1,
              width: '100%',
              fontSize: '12px',
              color: 'var(--text-primary)'
            }}
          />
        </div>

        {/* Action Buttons */}
        <button
          onClick={handleCapture}
          className="icon-btn"
          title="Capture Screenshot"
        >
          <Camera size={16} />
        </button>

        <button
          onClick={handleInspect}
          className="icon-btn"
          title="CDP DOM & Accessibility Inspection"
          style={{ color: isInspecting ? 'var(--accent-primary)' : undefined }}
        >
          <ShieldCheck size={16} />
        </button>

        <button
          onClick={toggleSidebar}
          className="icon-btn"
          style={{
            backgroundColor: sidebarOpen ? 'var(--bg-hover)' : 'transparent',
            color: sidebarOpen ? 'var(--accent-primary)' : undefined
          }}
          title="Toggle Navigation Sidebar"
        >
          <PanelLeft size={16} />
        </button>

        <button
          onClick={toggleAssistant}
          className="icon-btn"
          style={{
            backgroundColor: assistantOpen ? 'var(--bg-hover)' : 'transparent',
            color: assistantOpen ? 'var(--accent-primary)' : undefined
          }}
          title="Toggle AI Assistant"
        >
          <Sparkles size={16} />
        </button>
      </div>
    </div>
  );
};
