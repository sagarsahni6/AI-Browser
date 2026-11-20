import React, { useState } from 'react';
import {
  Search,
  Sparkles,
  Globe,
  Code2,
  BookOpen,
  Newspaper,
  Compass,
  ArrowRight
} from 'lucide-react';
import styles from './NewTabPage.module.css';

interface QuickSite {
  title: string;
  url: string;
  category: string;
}

const DEFAULT_SITES: QuickSite[] = [
  { title: 'Google', url: 'https://www.google.com', category: 'Search' },
  { title: 'GitHub', url: 'https://github.com', category: 'Dev' },
  { title: 'arXiv AI', url: 'https://arxiv.org/list/cs.AI/recent', category: 'Research' },
  { title: 'Wikipedia', url: 'https://en.wikipedia.org', category: 'Encyclopedia' },
  { title: 'Hacker News', url: 'https://news.ycombinator.com', category: 'Tech' },
  { title: 'TradingView', url: 'https://www.tradingview.com', category: 'Finance' },
  { title: 'Reddit', url: 'https://reddit.com', category: 'Community' },
  { title: 'YouTube', url: 'https://youtube.com', category: 'Media' },
];

export const NewTabPage: React.FC = () => {
  const [query, setQuery] = useState('');

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  const handleSearch = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const q = query.trim();
    if (!q) return;

    let targetUrl: string;
    if (q.startsWith('http://') || q.startsWith('https://')) {
      targetUrl = q;
    } else if (q.includes('.') && !q.includes(' ')) {
      targetUrl = `https://${q}`;
    } else {
      targetUrl = `https://www.google.com/search?q=${encodeURIComponent(q)}`;
    }

    if (window.electronAPI?.navigate) {
      window.electronAPI.navigate(targetUrl);
    } else {
      window.location.href = targetUrl;
    }
  };

  const handleOpenSite = (url: string) => {
    if (window.electronAPI?.navigate) {
      window.electronAPI.navigate(url);
    } else {
      window.location.href = url;
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.content}>
        {/* Hero Branding */}
        <div className={styles.hero}>
          <div className={styles.logoBadge}>
            <Sparkles size={28} />
          </div>
          <h1 className={styles.greeting}>{getGreeting()}</h1>
          <p className={styles.subtitle}>Autonomous Desktop Browser powered by Multi-Model AI</p>
        </div>

        {/* Search Bar */}
        <form onSubmit={handleSearch} style={{ width: '100%' }}>
          <div className={styles.searchBox}>
            <Search size={18} style={{ color: 'var(--text-muted)' }} />
            <input
              type="text"
              className={styles.searchInput}
              placeholder="Search the web or ask AI anything..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              autoFocus
            />
            <button type="submit" className={styles.searchBtn}>
              <span>Search</span>
              <ArrowRight size={13} />
            </button>
          </div>
        </form>

        {/* Quick Launch Grid */}
        <div className={styles.quickGrid}>
          {DEFAULT_SITES.map((site, idx) => (
            <div
              key={idx}
              className={styles.quickCard}
              onClick={() => handleOpenSite(site.url)}
            >
              <div className={styles.quickIcon}>
                {site.category === 'Dev' ? <Code2 size={18} /> :
                 site.category === 'Research' ? <BookOpen size={18} /> :
                 site.category === 'Tech' ? <Newspaper size={18} /> :
                 <Globe size={18} />}
              </div>
              <span className={styles.quickTitle}>{site.title}</span>
            </div>
          ))}
        </div>

        {/* Keyboard Shortcuts Hint */}
        <div className={styles.shortcutsRow}>
          <span><kbd className={styles.kbd}>Ctrl</kbd> + <kbd className={styles.kbd}>T</kbd> New Tab</span>
          <span><kbd className={styles.kbd}>Ctrl</kbd> + <kbd className={styles.kbd}>I</kbd> AI Assistant</span>
          <span><kbd className={styles.kbd}>Ctrl</kbd> + <kbd className={styles.kbd}>H</kbd> History</span>
        </div>
      </div>
    </div>
  );
};
