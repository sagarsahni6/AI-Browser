import React, { useState, useEffect, useRef } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  RotateCw,
  Plus,
  X,
  Lock,
  Globe,
  Camera,
  PanelLeft,
  Search,
  Sparkles,
  ShieldCheck,
  Star,
  Download,
  History,
  ShieldAlert,
  Clock,
  Bookmark,
  Sun,
  Moon
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
    isCurrentPageBookmarked,
    history,
    bookmarks,
    theme,
    toggleTheme,
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
    inspectPage,
    toggleBookmarkCurrentPage,
    refreshBookmarks,
    refreshHistory,
    setSidebarActiveTab
  } = useBrowserStore();

  const [addressInput, setAddressInput] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isInspecting, setIsInspecting] = useState(false);
  const suggestionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    refreshBookmarks();
    refreshHistory();
  }, [refreshBookmarks, refreshHistory]);

  useEffect(() => {
    if (activeTab?.url) {
      setAddressInput(activeTab.url);
    }
  }, [activeTab?.url]);

  const handleNavigateSubmit = (urlToNavigate?: string) => {
    let url = (urlToNavigate || addressInput).trim();
    setShowSuggestions(false);
    if (!url) return;

    if (!url.startsWith('http://') && !url.startsWith('https://') && !url.startsWith('about:')) {
      if (url.includes('.') && !url.includes(' ')) {
        url = 'https://' + url;
      } else {
        url = `https://www.google.com/search?q=${encodeURIComponent(url)}`;
      }
    }
    navigate(url);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleNavigateSubmit();
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
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

  // Filter suggestions from history and bookmarks
  const suggestions = React.useMemo(() => {
    const q = addressInput.toLowerCase().trim();
    if (!q || q === activeTab?.url?.toLowerCase()) return [];

    const matches: Array<{ title: string; url: string; type: 'history' | 'bookmark' }> = [];

    for (const b of bookmarks) {
      if (b.title.toLowerCase().includes(q) || b.url.toLowerCase().includes(q)) {
        matches.push({ title: b.title, url: b.url, type: 'bookmark' });
        if (matches.length >= 4) break;
      }
    }

    for (const h of history) {
      if (h.title.toLowerCase().includes(q) || h.url.toLowerCase().includes(q)) {
        if (!matches.some(m => m.url === h.url)) {
          matches.push({ title: h.title, url: h.url, type: 'history' });
        }
        if (matches.length >= 8) break;
      }
    }

    return matches;
  }, [addressInput, bookmarks, history, activeTab?.url]);

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      width: '100%',
      height: '100%',
      backgroundColor: 'var(--bg-primary)',
      borderBottom: '1px solid var(--border-subtle)',
      padding: '4px 8px 6px 8px',
      gap: '4px',
      position: 'relative'
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
                position: 'relative',
                overflow: 'hidden'
              }}
            >
              {tab.isLoading ? (
                <RotateCw size={12} className="animate-spin" style={{ color: 'var(--accent-primary)' }} />
              ) : tab.isPrivate ? (
                <ShieldAlert size={12} style={{ color: 'var(--warning)' }} />
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
                title="Close Tab (Ctrl+W)"
              >
                <X size={12} />
              </button>

              {/* Progress loading bar under active tab */}
              {tab.isLoading && (
                <div style={{
                  position: 'absolute',
                  bottom: 0,
                  left: 0,
                  height: '2px',
                  width: '100%',
                  backgroundColor: 'var(--accent-primary)',
                  animation: 'pulse 1s infinite'
                }} />
              )}
            </div>
          );
        })}

        <button
          onClick={() => createTab()}
          className="icon-btn"
          style={{ width: '28px', height: '28px' }}
          title="New Tab (Ctrl+T)"
        >
          <Plus size={14} />
        </button>

        <button
          onClick={() => createTab('https://duckduckgo.com', true)}
          className="icon-btn"
          style={{ width: '28px', height: '28px' }}
          title="New Private Tab"
        >
          <ShieldAlert size={13} style={{ color: 'var(--text-muted)' }} />
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
        width: '100%',
        position: 'relative'
      }}>
        <button
          onClick={goBack}
          disabled={!activeTab?.canGoBack}
          className="icon-btn"
          title="Back (Alt+Left)"
        >
          <ArrowLeft size={16} />
        </button>
        <button
          onClick={goForward}
          disabled={!activeTab?.canGoForward}
          className="icon-btn"
          title="Forward (Alt+Right)"
        >
          <ArrowRight size={16} />
        </button>
        <button
          onClick={reload}
          className="icon-btn"
          title="Reload (Ctrl+R)"
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
          gap: '8px',
          position: 'relative'
        }}>
          {addressInput.startsWith('https://') ? (
            <Lock size={13} style={{ color: 'var(--success)' }} />
          ) : (
            <Search size={13} style={{ color: 'var(--text-muted)' }} />
          )}
          <input
            type="text"
            value={addressInput}
            onChange={(e) => {
              setAddressInput(e.target.value);
              setShowSuggestions(true);
            }}
            onFocus={() => setShowSuggestions(true)}
            onKeyDown={handleKeyDown}
            placeholder="Search or enter URL..."
            style={{
              flex: 1,
              width: '100%',
              fontSize: '12px',
              color: 'var(--text-primary)'
            }}
          />

          {/* Bookmark Button */}
          <button
            onClick={toggleBookmarkCurrentPage}
            style={{
              padding: '4px',
              color: isCurrentPageBookmarked ? 'var(--warning)' : 'var(--text-muted)',
              cursor: 'pointer'
            }}
            title={isCurrentPageBookmarked ? 'Remove Bookmark' : 'Bookmark this tab'}
          >
            <Star size={14} fill={isCurrentPageBookmarked ? 'currentColor' : 'none'} />
          </button>
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
          title="Toggle Navigation Sidebar (Ctrl+H)"
        >
          <PanelLeft size={16} />
        </button>

        <button
          onClick={toggleTheme}
          className="icon-btn"
          title={theme === 'light' ? 'Switch to Dark Theme' : 'Switch to Light Theme'}
          aria-label="Toggle Theme"
        >
          {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
        </button>

        <button
          onClick={toggleAssistant}
          className="icon-btn"
          style={{
            backgroundColor: assistantOpen ? 'var(--bg-hover)' : 'transparent',
            color: assistantOpen ? 'var(--accent-primary)' : undefined
          }}
          title="Toggle AI Assistant (Ctrl+I)"
        >
          <Sparkles size={16} />
        </button>
      </div>

      {/* Autocomplete Suggestions Dropdown */}
      {showSuggestions && suggestions.length > 0 && (
        <div
          ref={suggestionRef}
          style={{
            position: 'absolute',
            top: '72px',
            left: '110px',
            right: '160px',
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--border-strong)',
            borderRadius: 'var(--radius-md)',
            boxShadow: 'var(--shadow-lg)',
            zIndex: 9999,
            padding: '6px 0',
            maxHeight: '260px',
            overflowY: 'auto'
          }}
        >
          {suggestions.map((item, idx) => (
            <div
              key={idx}
              onClick={() => handleNavigateSubmit(item.url)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px 12px',
                cursor: 'pointer',
                fontSize: '12px',
                color: 'var(--text-primary)',
                transition: 'background-color 100ms ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--bg-hover)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              {item.type === 'bookmark' ? (
                <Bookmark size={13} style={{ color: 'var(--warning)', flexShrink: 0 }} />
              ) : (
                <Clock size={13} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
              )}
              <span style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '240px' }}>
                {item.title}
              </span>
              <span style={{ color: 'var(--text-secondary)', fontSize: '11px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                {item.url}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
