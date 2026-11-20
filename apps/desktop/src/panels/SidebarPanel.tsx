import React, { useEffect, useState } from 'react';
import {
  History,
  Bookmark,
  Download,
  FolderGit2,
  ListTodo,
  Settings,
  Sparkles,
  Trash2,
  ExternalLink,
  Search,
  Folder,
  FileCheck
} from 'lucide-react';
import { useBrowserStore } from '../store/browser-store';
import { SettingsView } from '../components/SettingsView';
import { TaskPanel } from '../components/TaskPanel';
import { CollectionsPanel } from '../components/CollectionsPanel';
import styles from './SidebarPanel.module.css';

const cx = (...classes: (string | false | undefined | null)[]) => classes.filter(Boolean).join(' ');

export const SidebarPanel: React.FC = () => {
  const {
    sidebarActiveTab,
    setSidebarActiveTab,
    history,
    bookmarks,
    downloads,
    createTab,
    refreshHistory,
    searchHistory,
    clearHistory,
    refreshBookmarks,
    removeBookmark,
    refreshDownloads,
    openDownloadFile,
    openDownloadFolder
  } = useBrowserStore();

  const [historySearchQuery, setHistorySearchQuery] = useState('');

  useEffect(() => {
    refreshBookmarks();
    refreshHistory();
    refreshDownloads();
  }, [refreshBookmarks, refreshHistory, refreshDownloads]);

  const navItems = [
    { id: 'discover' as const, icon: Sparkles, label: 'AI Search' },
    { id: 'history' as const, icon: History, label: 'History' },
    { id: 'bookmarks' as const, icon: Bookmark, label: 'Bookmarks' },
    { id: 'downloads' as const, icon: Download, label: 'Downloads' },
    { id: 'collections' as const, icon: FolderGit2, label: 'Collections' },
    { id: 'tasks' as const, icon: ListTodo, label: 'Agent Tasks' },
  ];

  const handleOpenUrl = (url: string) => {
    createTab(url);
  };

  const handleHistorySearchChange = (val: string) => {
    setHistorySearchQuery(val);
    searchHistory(val);
  };

  return (
    <div className={styles.sidebar}>
      {/* Top Branding Header */}
      <div className={styles.brand}>
        <div className={styles.brandLogo}>
          AI
        </div>
        <span className={styles.brandText}>
          AI Browser
        </span>
      </div>

      {/* Navigation tabs strip */}
      <div className={styles.navStrip}>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = sidebarActiveTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setSidebarActiveTab(item.id)}
              className={cx(styles.navBtn, isActive && styles.navBtnActive)}
            >
              <Icon size={14} style={{ color: isActive ? 'var(--accent-primary)' : undefined }} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      {/* Main Content Area based on sidebarActiveTab */}
      <div className={styles.contentArea}>
        {/* DISCOVER TAB */}
        {sidebarActiveTab === 'discover' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div className={styles.sectionHeader}>
              Quick Launch
            </div>
            {[
              { title: 'Google Search', url: 'https://google.com' },
              { title: 'GitHub', url: 'https://github.com' },
              { title: 'Hacker News', url: 'https://news.ycombinator.com' },
              { title: 'Wikipedia', url: 'https://en.wikipedia.org' },
              { title: 'arXiv AI Papers', url: 'https://arxiv.org/list/cs.AI/recent' },
            ].map((link, idx) => (
              <div
                key={idx}
                onClick={() => handleOpenUrl(link.url)}
                className={styles.cardItem}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <span>{link.title}</span>
                <ExternalLink size={11} style={{ opacity: 0.5 }} />
              </div>
            ))}
          </div>
        )}

        {/* HISTORY TAB */}
        {sidebarActiveTab === 'history' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div className={styles.sectionHeader}>
              <span>Browsing History</span>
              {history.length > 0 && (
                <button
                  onClick={clearHistory}
                  style={{ fontSize: '11px', color: 'var(--error)', display: 'flex', alignItems: 'center', gap: '3px' }}
                  title="Clear All History"
                >
                  <Trash2 size={11} /> Clear
                </button>
              )}
            </div>

            {/* Search Box */}
            <div className={styles.searchBox}>
              <Search size={12} style={{ color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Search history..."
                value={historySearchQuery}
                onChange={(e) => handleHistorySearchChange(e.target.value)}
                className={styles.searchInput}
              />
            </div>

            {/* History List */}
            {history.length === 0 ? (
              <div className={styles.emptyState}>
                No history entries found.
              </div>
            ) : (
              history.map((item) => (
                <div
                  key={item.id}
                  onClick={() => handleOpenUrl(item.url)}
                  className={styles.cardItem}
                  style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}
                >
                  <span className="truncate" style={{ fontWeight: 500 }}>
                    {item.title}
                  </span>
                  <span className="truncate" style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                    {item.url}
                  </span>
                </div>
              ))
            )}
          </div>
        )}

        {/* BOOKMARKS TAB */}
        {sidebarActiveTab === 'bookmarks' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div className={styles.sectionHeader}>
              Saved Bookmarks ({bookmarks.length})
            </div>

            {bookmarks.length === 0 ? (
              <div className={styles.emptyState}>
                No bookmarks yet. Click the star in the toolbar to save pages.
              </div>
            ) : (
              bookmarks.map((bm) => (
                <div
                  key={bm.id}
                  className={styles.cardItem}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '6px'
                  }}
                >
                  <div
                    onClick={() => handleOpenUrl(bm.url)}
                    style={{ flex: 1, overflow: 'hidden', cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: '2px' }}
                  >
                    <span className="truncate" style={{ fontWeight: 500 }}>
                      {bm.title}
                    </span>
                    <span className="truncate" style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                      {bm.url}
                    </span>
                  </div>
                  <button
                    onClick={() => removeBookmark(bm.id)}
                    style={{ color: 'var(--text-muted)', padding: '2px' }}
                    title="Remove Bookmark"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))
            )}
          </div>
        )}

        {/* DOWNLOADS TAB */}
        {sidebarActiveTab === 'downloads' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div className={styles.sectionHeader}>
              Downloads
            </div>

            {downloads.length === 0 ? (
              <div className={styles.emptyState}>
                No active or completed downloads.
              </div>
            ) : (
              downloads.map((dl) => (
                <div
                  key={dl.id}
                  className={styles.downloadCard}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span className="truncate" style={{ fontWeight: 600 }}>
                      {dl.filename}
                    </span>
                    <span style={{
                      fontSize: '10px',
                      color: dl.state === 'completed' ? 'var(--success)' : 'var(--warning)',
                      textTransform: 'capitalize'
                    }}>
                      {dl.state}
                    </span>
                  </div>

                  <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                    {Math.round(dl.receivedBytes / 1024)} KB
                    {dl.totalBytes > 0 && ` / ${Math.round(dl.totalBytes / 1024)} KB`}
                  </div>

                  {/* Actions */}
                  {dl.state === 'completed' && (
                    <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
                      <button
                        onClick={() => openDownloadFile(dl.id)}
                        style={{
                          fontSize: '10.5px',
                          padding: '2px 6px',
                          backgroundColor: 'var(--bg-hover)',
                          borderRadius: 'var(--radius-sm)',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}
                      >
                        <FileCheck size={11} /> Open File
                      </button>
                      <button
                        onClick={() => openDownloadFolder(dl.id)}
                        style={{
                          fontSize: '10.5px',
                          padding: '2px 6px',
                          backgroundColor: 'var(--bg-hover)',
                          borderRadius: 'var(--radius-sm)',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}
                      >
                        <Folder size={11} /> Show in Folder
                      </button>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {/* SETTINGS VIEW */}
        {sidebarActiveTab === 'settings' && (
          <SettingsView />
        )}

        {/* AGENT TASKS TAB */}
        {sidebarActiveTab === 'tasks' && (
          <TaskPanel />
        )}

        {/* COLLECTIONS TAB */}
        {sidebarActiveTab === 'collections' && (
          <CollectionsPanel />
        )}
      </div>

      {/* Footer Settings Button */}
      <div className={styles.footer}>
        <button
          onClick={() => setSidebarActiveTab('settings')}
          className={styles.navBtn}
        >
          <Settings size={14} />
          <span>Settings</span>
        </button>
      </div>
    </div>
  );
};
