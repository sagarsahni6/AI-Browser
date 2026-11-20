import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Search,
  Sparkles,
  Globe,
  Star,
  History,
  ShieldCheck,
  Camera,
  FileText,
  Table,
  Sun,
  Moon,
  Trash2,
  Plus,
  ArrowRight
} from 'lucide-react';
import { useBrowserStore } from '../store/browser-store';
import styles from './CommandPalette.module.css';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

interface CommandItem {
  id: string;
  category: 'Actions' | 'Open Tabs' | 'Bookmarks' | 'History';
  title: string;
  subtitle?: string;
  icon: React.ReactNode;
  action: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose }) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const {
    tabs,
    switchTab,
    createTab,
    bookmarks,
    history,
    theme,
    toggleTheme,
    navigate,
    sendChatMessage,
    capturePage,
    inspectPage,
    clearHistory
  } = useBrowserStore();

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const allItems: CommandItem[] = useMemo(() => {
    const items: CommandItem[] = [];

    // 1. Built-in AI & Browser Actions
    items.push(
      {
        id: 'action-summarize',
        category: 'Actions',
        title: 'Summarize Active Webpage',
        subtitle: 'AI Research Assistant',
        icon: <FileText size={14} style={{ color: 'var(--accent-primary)' }} />,
        action: () => {
          onClose();
          sendChatMessage('Summarize the current page with key takeaways and bullet points.');
        }
      },
      {
        id: 'action-extract-table',
        category: 'Actions',
        title: 'Extract Tabular / Option Chain Data',
        subtitle: 'Autonomous Data Agent',
        icon: <Table size={14} style={{ color: '#f59e0b' }} />,
        action: () => {
          onClose();
          sendChatMessage('Extract table data from this page and export to CSV.');
        }
      },
      {
        id: 'action-screenshot',
        category: 'Actions',
        title: 'Capture Viewport Screenshot',
        subtitle: 'Browser Observation',
        icon: <Camera size={14} />,
        action: () => {
          onClose();
          capturePage();
        }
      },
      {
        id: 'action-inspect',
        category: 'Actions',
        title: 'Inspect Page Elements with CDP',
        subtitle: 'DevTools Protocol',
        icon: <ShieldCheck size={14} style={{ color: 'var(--success)' }} />,
        action: () => {
          onClose();
          inspectPage();
        }
      },
      {
        id: 'action-new-tab',
        category: 'Actions',
        title: 'Open New Tab',
        subtitle: 'Ctrl+T',
        icon: <Plus size={14} />,
        action: () => {
          onClose();
          createTab();
        }
      },
      {
        id: 'action-private-tab',
        category: 'Actions',
        title: 'Open New Private Tab',
        subtitle: 'Isolated session',
        icon: <Globe size={14} style={{ color: 'var(--warning)' }} />,
        action: () => {
          onClose();
          createTab('https://duckduckgo.com', true);
        }
      },
      {
        id: 'action-toggle-theme',
        category: 'Actions',
        title: theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode',
        subtitle: 'Appearance',
        icon: theme === 'light' ? <Moon size={14} /> : <Sun size={14} />,
        action: () => {
          onClose();
          toggleTheme();
        }
      },
      {
        id: 'action-clear-history',
        category: 'Actions',
        title: 'Clear All Browsing History',
        subtitle: 'Privacy',
        icon: <Trash2 size={14} style={{ color: 'var(--error)' }} />,
        action: () => {
          onClose();
          clearHistory();
        }
      }
    );

    // 2. Open Tabs
    for (const t of tabs) {
      items.push({
        id: `tab-${t.id}`,
        category: 'Open Tabs',
        title: t.title || 'Untitled Tab',
        subtitle: t.url,
        icon: <Globe size={14} style={{ opacity: 0.8 }} />,
        action: () => {
          onClose();
          switchTab(t.id);
        }
      });
    }

    // 3. Bookmarks
    for (const b of bookmarks) {
      items.push({
        id: `bm-${b.id}`,
        category: 'Bookmarks',
        title: b.title,
        subtitle: b.url,
        icon: <Star size={14} style={{ color: 'var(--warning)' }} />,
        action: () => {
          onClose();
          navigate(b.url);
        }
      });
    }

    // 4. History (Top 15)
    for (const h of history.slice(0, 15)) {
      items.push({
        id: `hist-${h.id}`,
        category: 'History',
        title: h.title,
        subtitle: h.url,
        icon: <History size={14} style={{ color: 'var(--text-muted)' }} />,
        action: () => {
          onClose();
          navigate(h.url);
        }
      });
    }

    return items;
  }, [tabs, bookmarks, history, theme, onClose, switchTab, createTab, navigate, sendChatMessage, capturePage, inspectPage, toggleTheme, clearHistory]);

  const filteredItems = useMemo(() => {
    const q = query.toLowerCase().trim();
    if (!q) return allItems.slice(0, 16);

    return allItems
      .filter(item => item.title.toLowerCase().includes(q) || (item.subtitle && item.subtitle.toLowerCase().includes(q)))
      .slice(0, 16);
  }, [allItems, query]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [filteredItems]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev + 1) % (filteredItems.length || 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev - 1 + filteredItems.length) % (filteredItems.length || 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredItems[selectedIndex]) {
        filteredItems[selectedIndex].action();
      } else if (query.trim()) {
        // Direct search or navigate
        onClose();
        let target = query.trim();
        if (!target.startsWith('http://') && !target.startsWith('https://')) {
          if (target.includes('.') && !target.includes(' ')) {
            target = `https://${target}`;
          } else {
            target = `https://www.google.com/search?q=${encodeURIComponent(target)}`;
          }
        }
        navigate(target);
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={`${styles.palette} animate-scale-in`} onClick={e => e.stopPropagation()}>
        {/* Search Input Bar */}
        <div className={styles.searchHeader}>
          <Search size={16} style={{ color: 'var(--accent-primary)' }} />
          <input
            ref={inputRef}
            type="text"
            className={styles.searchInput}
            placeholder="Type a command, search tabs, bookmarks, or web..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>

        {/* Results List */}
        <div className={styles.resultsList}>
          {filteredItems.length === 0 ? (
            <div style={{ padding: '20px', textAlign: 'center', fontSize: '12px', color: 'var(--text-muted)' }}>
              Press Enter to search Google for "<strong>{query}</strong>"
            </div>
          ) : (
            filteredItems.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={item.id}
                  className={`${styles.resultItem} ${isSelected ? styles.resultItemActive : ''}`}
                  onClick={() => item.action()}
                  onMouseEnter={() => setSelectedIndex(idx)}
                >
                  <div className={styles.resultItemLeft}>
                    {item.icon}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', overflow: 'hidden' }}>
                      <span className={styles.resultTitle}>{item.title}</span>
                      {item.subtitle && <span className={styles.resultSubtitle}>{item.subtitle}</span>}
                    </div>
                  </div>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    {item.category}
                  </span>
                </div>
              );
            })
          )}
        </div>

        {/* Footer shortcuts */}
        <div className={styles.footer}>
          <span><kbd className={styles.kbd}>↑</kbd> <kbd className={styles.kbd}>↓</kbd> to navigate</span>
          <span><kbd className={styles.kbd}>Enter</kbd> to select</span>
          <span><kbd className={styles.kbd}>Esc</kbd> to close</span>
        </div>
      </div>
    </div>
  );
};
