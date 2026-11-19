import React, { useEffect, useState } from 'react';
import {
  Compass,
  History,
  Bookmark,
  Download,
  BookOpen,
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

export const SidebarPanel: React.FC = () => {
  const {
    sidebarActiveTab,
    setSidebarActiveTab,
    history,
    bookmarks,
    downloads,
    createTab,
    navigate,
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
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      width: '100%',
      height: '100%',
      backgroundColor: 'var(--bg-secondary)',
      borderRight: '1px solid var(--border-subtle)',
      padding: '8px'
    }}>
      {/* Top Branding Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '4px 6px 10px 6px',
        borderBottom: '1px solid var(--border-subtle)',
        marginBottom: '8px'
      }}>
        <div style={{
          width: '24px',
          height: '24px',
          borderRadius: 'var(--radius-sm)',
          backgroundColor: 'var(--accent-primary)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontWeight: 'bold',
          fontSize: '12px'
        }}>
          AI
        </div>
        <span style={{ fontWeight: 600, fontSize: '13px', letterSpacing: '-0.2px' }}>
          AI Browser
        </span>
      </div>

      {/* Navigation tabs strip */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', marginBottom: '8px' }}>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = sidebarActiveTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setSidebarActiveTab(item.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px 8px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: isActive ? 'var(--bg-tertiary)' : 'transparent',
                color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontSize: '11.5px',
                width: '100%',
                justifyContent: 'flex-start'
              }}
            >
              <Icon size={14} style={{ color: isActive ? 'var(--accent-primary)' : undefined }} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      {/* Main Content Area based on sidebarActiveTab */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        borderTop: '1px solid var(--border-subtle)',
        paddingTop: '8px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      }}>
        {/* DISCOVER TAB */}
        {sidebarActiveTab === 'discover' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>
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
                style={{
                  padding: '6px 8px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'var(--bg-tertiary)',
                  fontSize: '11.5px',
                  cursor: 'pointer',
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
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>
                Browsing History
              </span>
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
            <div style={{
              display: 'flex',
              alignItems: 'center',
              backgroundColor: 'var(--bg-tertiary)',
              borderRadius: 'var(--radius-sm)',
              padding: '4px 6px',
              gap: '6px'
            }}>
              <Search size={12} style={{ color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Search history..."
                value={historySearchQuery}
                onChange={(e) => handleHistorySearchChange(e.target.value)}
                style={{ fontSize: '11px', width: '100%', color: 'var(--text-primary)' }}
              />
            </div>

            {/* History List */}
            {history.length === 0 ? (
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center', padding: '16px 0' }}>
                No history entries found.
              </div>
            ) : (
              history.map((item) => (
                <div
                  key={item.id}
                  onClick={() => handleOpenUrl(item.url)}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    padding: '6px 8px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: 'var(--bg-tertiary)',
                    cursor: 'pointer',
                    fontSize: '11.5px',
                    gap: '2px'
                  }}
                >
                  <span style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.title}
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
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
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>
              Saved Bookmarks ({bookmarks.length})
            </span>

            {bookmarks.length === 0 ? (
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center', padding: '16px 0' }}>
                No bookmarks yet. Click the star in the toolbar to save pages.
              </div>
            ) : (
              bookmarks.map((bm) => (
                <div
                  key={bm.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '6px 8px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: 'var(--bg-tertiary)',
                    fontSize: '11.5px',
                    gap: '6px'
                  }}
                >
                  <div
                    onClick={() => handleOpenUrl(bm.url)}
                    style={{ flex: 1, overflow: 'hidden', cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: '2px' }}
                  >
                    <span style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {bm.title}
                    </span>
                    <span style={{ fontSize: '10px', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
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
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>
              Downloads
            </span>

            {downloads.length === 0 ? (
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center', padding: '16px 0' }}>
                No active or completed downloads.
              </div>
            ) : (
              downloads.map((dl) => (
                <div
                  key={dl.id}
                  style={{
                    padding: '8px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: 'var(--bg-tertiary)',
                    fontSize: '11.5px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
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

        {/* COLLECTIONS & TASKS PLACEHOLDER */}
        {(sidebarActiveTab === 'collections' || sidebarActiveTab === 'tasks') && (
          <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', textAlign: 'center', padding: '24px 8px' }}>
            {sidebarActiveTab === 'collections'
              ? 'Saved Research Collections will appear here once saved from the AI Assistant.'
              : 'Autonomous Agent Tasks and execution plans will appear here.'}
          </div>
        )}
      </div>

      {/* Footer Settings Button */}
      <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '6px' }}>
        <button
          onClick={() => setSidebarActiveTab('settings')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 8px',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--text-secondary)',
            fontSize: '11.5px',
            width: '100%',
            justifyContent: 'flex-start'
          }}
        >
          <Settings size={14} />
          <span>Settings</span>
        </button>
      </div>
    </div>
  );
};
