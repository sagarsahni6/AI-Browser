import React, { useState, useEffect, useRef, useMemo } from 'react';
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
  ShieldAlert,
  Clock,
  Bookmark,
  Sun,
  Moon,
  Pin,
  Copy,
  BookOpen,
  Workflow as WorkflowIcon,
  ListTodo,
  Settings
} from 'lucide-react';
import { useBrowserStore } from '../store/browser-store';
import { CommandPalette } from '../components/CommandPalette';
import styles from './ToolbarPanel.module.css';

const cx = (...classes: (string | false | undefined | null)[]) => classes.filter(Boolean).join(' ');

export const ToolbarPanel: React.FC = () => {
  const {
    tabs,
    activeTabId,
    activeTab,
    sidebarOpen,
    sidebarActiveTab,
    setSidebarActiveTab,
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
    duplicateTab,
    setTabPinned,
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
    refreshHistory
  } = useBrowserStore();

  const [addressInput, setAddressInput] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isInspecting, setIsInspecting] = useState(false);
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [tabContextMenu, setTabContextMenu] = useState<{ x: number; y: number; tabId: string } | null>(null);
  const suggestionRef = useRef<HTMLDivElement>(null);

  const sortedTabs = useMemo(() => {
    return [...tabs].sort((a, b) => {
      if (a.isPinned && !b.isPinned) return -1;
      if (!a.isPinned && b.isPinned) return 1;
      return 0;
    });
  }, [tabs]);

  useEffect(() => {
    const handleCloseMenu = () => setTabContextMenu(null);
    window.addEventListener('click', handleCloseMenu);
    return () => window.removeEventListener('click', handleCloseMenu);
  }, []);

  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setShowCommandPalette(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleGlobalKeyDown);
    const unsubPalette = window.electronAPI?.onToggleCommandPalette?.(() => {
      setShowCommandPalette(prev => !prev);
    });

    return () => {
      window.removeEventListener('keydown', handleGlobalKeyDown);
      unsubPalette?.();
    };
  }, []);

  useEffect(() => {
    refreshBookmarks();
    refreshHistory();
  }, [refreshBookmarks, refreshHistory]);

  useEffect(() => {
    if (activeTab?.url) {
      if (activeTab.url.includes('panel=newtab')) {
        setAddressInput('');
      } else {
        setAddressInput(activeTab.url);
      }
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
  const suggestions = useMemo(() => {
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
    <div className={styles.toolbar}>
      {/* Top Tabs Row */}
      <div className={styles.tabStrip}>
        {sortedTabs.map(tab => {
          const isActive = tab.id === activeTabId;
          return (
            <div
              key={tab.id}
              onClick={() => switchTab(tab.id)}
              onContextMenu={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setTabContextMenu({ x: e.clientX, y: e.clientY, tabId: tab.id });
              }}
              className={cx(
                styles.tab,
                isActive && styles.tabActive,
                tab.isPinned && styles.tabPinned
              )}
              title={`${tab.title || 'New Tab'} - ${tab.url}${tab.isPinned ? ' (Pinned)' : ''}`}
            >
              {tab.isLoading ? (
                <RotateCw size={12} className="animate-spin" style={{ color: 'var(--accent-primary)' }} />
              ) : tab.isPinned ? (
                <Pin size={12} style={{ color: 'var(--accent-primary)' }} />
              ) : tab.isPrivate ? (
                <ShieldAlert size={12} style={{ color: 'var(--warning)' }} />
              ) : tab.favicon ? (
                <img
                  src={tab.favicon}
                  alt=""
                  className={styles.tabFavicon}
                  onError={(e) => {
                    (e.currentTarget as HTMLImageElement).style.display = 'none';
                  }}
                />
              ) : (
                <Globe size={12} style={{ opacity: 0.7 }} />
              )}
              {!tab.isPinned && (
                <span className={styles.tabTitle}>
                  {tab.title || 'New Tab'}
                </span>
              )}
              {!tab.isPinned && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    closeTab(tab.id);
                  }}
                  className={styles.tabClose}
                  title="Close Tab (Ctrl+W)"
                >
                  <X size={12} />
                </button>
              )}

              {/* Progress loading bar under active tab */}
              {tab.isLoading && (
                <div className={styles.tabProgress} />
              )}
            </div>
          );
        })}

        {/* Tab Context Menu */}
        {tabContextMenu && (() => {
          const targetTab = tabs.find(t => t.id === tabContextMenu.tabId);
          if (!targetTab) return null;
          return (
            <div
              className={styles.contextMenu}
              style={{
                top: `${tabContextMenu.y}px`,
                left: `${tabContextMenu.x}px`
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <button
                className={styles.contextMenuItem}
                onClick={() => {
                  setTabPinned(targetTab.id, !targetTab.isPinned);
                  setTabContextMenu(null);
                }}
              >
                <Pin size={12} />
                <span>{targetTab.isPinned ? 'Unpin Tab' : 'Pin Tab'}</span>
              </button>
              <button
                className={styles.contextMenuItem}
                onClick={() => {
                  duplicateTab(targetTab.id);
                  setTabContextMenu(null);
                }}
              >
                <Copy size={12} />
                <span>Duplicate Tab</span>
              </button>
              <button
                className={styles.contextMenuItem}
                onClick={() => {
                  reload();
                  setTabContextMenu(null);
                }}
              >
                <RotateCw size={12} />
                <span>Reload Tab</span>
              </button>
              <div className={styles.contextMenuDivider} />
              <button
                className={styles.contextMenuItem}
                disabled={targetTab.isPinned}
                onClick={() => {
                  closeTab(targetTab.id);
                  setTabContextMenu(null);
                }}
              >
                <X size={12} />
                <span>Close Tab</span>
              </button>
              <button
                className={styles.contextMenuItem}
                onClick={() => {
                  for (const t of tabs) {
                    if (t.id !== targetTab.id && !t.isPinned) {
                      closeTab(t.id);
                    }
                  }
                  setTabContextMenu(null);
                }}
              >
                <span>Close Other Tabs</span>
              </button>
            </div>
          );
        })()}

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

        {/* Quick Access Feature Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '3px', marginRight: '6px' }}>
          <button
            onClick={() => setSidebarActiveTab('research')}
            className={cx(styles.featurePill, sidebarOpen && sidebarActiveTab === 'research' && styles.featurePillActive)}
            title="Open Deep Research & Document Intelligence"
          >
            <BookOpen size={12} />
            <span>Research</span>
          </button>

          <button
            onClick={() => setSidebarActiveTab('workflows')}
            className={cx(styles.featurePill, sidebarOpen && sidebarActiveTab === 'workflows' && styles.featurePillActive)}
            title="Open Workflow Recorder & Visual Builder"
          >
            <WorkflowIcon size={12} />
            <span>Workflows</span>
          </button>

          <button
            onClick={() => setSidebarActiveTab('tasks')}
            className={cx(styles.featurePill, sidebarOpen && sidebarActiveTab === 'tasks' && styles.featurePillActive)}
            title="Open Agent Task Queue & Execution Dashboard"
          >
            <ListTodo size={12} />
            <span>Tasks</span>
          </button>

          <button
            onClick={() => setSidebarActiveTab('settings')}
            className={cx(styles.featurePill, sidebarOpen && sidebarActiveTab === 'settings' && styles.featurePillActive)}
            title="Open Browser & Agent Settings"
          >
            <Settings size={12} />
            <span>Settings</span>
          </button>
        </div>

        {/* Backend Status indicator */}
        <div className={styles.statusBadge}>
          <span
            className={cx(
              styles.statusDot,
              backendStatus.online ? styles.statusDotOnline : styles.statusDotOffline
            )}
          />
          <span>{backendStatus.online ? `Python :${backendStatus.port || 8000}` : 'Offline'}</span>
        </div>
      </div>

      {/* Bottom Navigation & Omnibox Row */}
      <div className={styles.navRow}>
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
        <div className={styles.omnibox}>
          {addressInput.startsWith('https://') ? (
            <Lock size={13} style={{ color: 'var(--success)' }} />
          ) : (
            <Search size={13} style={{ color: 'var(--text-muted)' }} />
          )}
          <input
            type="text"
            className={styles.omniboxInput}
            value={addressInput}
            onChange={(e) => {
              setAddressInput(e.target.value);
              setShowSuggestions(true);
            }}
            onFocus={() => setShowSuggestions(true)}
            onKeyDown={handleKeyDown}
            placeholder="Search or enter URL..."
          />

          {/* Bookmark Button */}
          <button
            onClick={toggleBookmarkCurrentPage}
            className={styles.bookmarkBtn}
            style={{
              color: isCurrentPageBookmarked ? 'var(--warning)' : 'var(--text-muted)'
            }}
            title={isCurrentPageBookmarked ? 'Remove Bookmark' : 'Bookmark this tab'}
          >
            <Star size={14} fill={isCurrentPageBookmarked ? 'currentColor' : 'none'} />
          </button>

          {/* Command Palette Trigger Badge */}
          <button
            onClick={() => setShowCommandPalette(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '2px',
              padding: '2px 5px',
              borderRadius: '4px',
              backgroundColor: 'var(--bg-tertiary)',
              border: '1px solid var(--border-subtle)',
              fontSize: '10px',
              color: 'var(--text-secondary)',
              cursor: 'pointer'
            }}
            title="Open Command Palette (Ctrl+K)"
          >
            <span>Ctrl K</span>
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
        <div ref={suggestionRef} className={cx(styles.suggestions, 'animate-slide-in-down')}>
          {suggestions.map((item, idx) => (
            <div
              key={idx}
              onClick={() => handleNavigateSubmit(item.url)}
              className={styles.suggestionItem}
            >
              {item.type === 'bookmark' ? (
                <Bookmark size={13} style={{ color: 'var(--warning)', flexShrink: 0 }} />
              ) : (
                <Clock size={13} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
              )}
              <span className={styles.suggestionTitle}>
                {item.title}
              </span>
              <span className={styles.suggestionUrl}>
                {item.url}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Command Palette Modal */}
      <CommandPalette
        isOpen={showCommandPalette}
        onClose={() => setShowCommandPalette(false)}
      />
    </div>
  );
};
