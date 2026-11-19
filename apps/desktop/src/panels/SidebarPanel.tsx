import React from 'react';
import {
  Compass,
  History,
  Bookmark,
  Download,
  BookOpen,
  FolderGit2,
  ListTodo,
  Settings,
  Sparkles
} from 'lucide-react';

export const SidebarPanel: React.FC = () => {
  const navItems = [
    { icon: Sparkles, label: 'AI Search', active: true },
    { icon: Compass, label: 'Discover' },
    { icon: History, label: 'History' },
    { icon: Bookmark, label: 'Bookmarks' },
    { icon: Download, label: 'Downloads' },
    { icon: BookOpen, label: 'Saved Pages' },
    { icon: FolderGit2, label: 'Research Collections' },
    { icon: ListTodo, label: 'Agent Tasks' },
  ];

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      width: '100%',
      height: '100%',
      backgroundColor: 'var(--bg-secondary)',
      borderRight: '1px solid var(--border-subtle)',
      padding: '12px 8px'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '0 8px 12px 8px',
        borderBottom: '1px solid var(--border-subtle)',
        marginBottom: '12px'
      }}>
        <div style={{
          width: '28px',
          height: '28px',
          borderRadius: 'var(--radius-sm)',
          backgroundColor: 'var(--accent-primary)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontWeight: 'bold',
          fontSize: '14px'
        }}>
          AI
        </div>
        <span style={{ fontWeight: 600, fontSize: '14px', letterSpacing: '-0.2px' }}>
          Browser
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
        {navItems.map((item, idx) => {
          const Icon = item.icon;
          return (
            <button
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '8px 10px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: item.active ? 'var(--bg-tertiary)' : 'transparent',
                color: item.active ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontSize: '12px',
                width: '100%',
                justifyContent: 'flex-start'
              }}
            >
              <Icon size={16} style={{ color: item.active ? 'var(--accent-primary)' : undefined }} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '8px' }}>
        <button
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '8px 10px',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--text-secondary)',
            fontSize: '12px',
            width: '100%',
            justifyContent: 'flex-start'
          }}
        >
          <Settings size={16} />
          <span>Settings</span>
        </button>
      </div>
    </div>
  );
};
