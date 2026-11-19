import React, { useState, useEffect } from 'react';
import {
  Shield,
  Key,
  Database,
  Cpu,
  CheckCircle,
  AlertCircle,
  Trash2,
  Save,
  Globe,
  Sliders,
  Sun,
  Moon
} from 'lucide-react';
import { useBrowserStore } from '../store/browser-store';

export const SettingsView: React.FC = () => {
  const { clearHistory, theme, setTheme } = useBrowserStore();

  const [activeTab, setActiveTab] = useState<'general' | 'ai' | 'privacy' | 'about'>('ai');
  const [nvidiaKey, setNvidiaKey] = useState('');
  const [selectedModel, setSelectedModel] = useState('meta/llama-3.3-70b-instruct');
  const [searchEngine, setSearchEngine] = useState('duckduckgo');
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
  const [testingConnection, setTestingConnection] = useState(false);

  useEffect(() => {
    if (window.electronAPI?.getSecret) {
      window.electronAPI.getSecret('NVIDIA_API_KEY').then(key => {
        if (key) setNvidiaKey(key);
      });
    }
  }, []);

  const handleSaveNvidiaKey = async () => {
    if (window.electronAPI?.setSecret) {
      await window.electronAPI.setSecret('NVIDIA_API_KEY', nvidiaKey);
      setStatusMessage({ text: 'NVIDIA NIM credentials safely stored using Windows DPAPI.', type: 'success' });
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  const handleTestConnection = async () => {
    setTestingConnection(true);
    setStatusMessage(null);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/providers/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider_id: 'nvidia_nim',
          api_key: nvidiaKey
        })
      });
      const data = await res.json();
      if (data.success) {
        setStatusMessage({ text: 'Connection successful! NVIDIA NIM API verified.', type: 'success' });
      } else {
        setStatusMessage({ text: `Connection failed: ${data.message}`, type: 'error' });
      }
    } catch (err: any) {
      setStatusMessage({ text: `Error contacting backend: ${err.message}`, type: 'error' });
    } finally {
      setTestingConnection(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: 'var(--bg-secondary)',
      fontSize: '12px'
    }}>
      {/* Sub-nav tabs */}
      <div style={{
        display: 'flex',
        borderBottom: '1px solid var(--border-subtle)',
        padding: '0 8px',
        backgroundColor: 'var(--bg-primary)'
      }}>
        {[
          { id: 'ai' as const, label: 'AI Providers', icon: Cpu },
          { id: 'general' as const, label: 'General', icon: Sliders },
          { id: 'privacy' as const, label: 'Privacy & Data', icon: Shield },
          { id: 'about' as const, label: 'About', icon: Globe },
        ].map(t => {
          const Icon = t.icon;
          const isSelected = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 10px',
                borderBottom: isSelected ? '2px solid var(--accent-primary)' : '2px solid transparent',
                color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontWeight: isSelected ? 600 : 400,
                fontSize: '11.5px'
              }}
            >
              <Icon size={13} />
              <span>{t.label}</span>
            </button>
          );
        })}
      </div>

      {/* Content Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {statusMessage && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '8px 10px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: statusMessage.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
            color: statusMessage.type === 'success' ? 'var(--success)' : 'var(--error)',
            fontSize: '11.5px'
          }}>
            {statusMessage.type === 'success' ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
            <span>{statusMessage.text}</span>
          </div>
        )}

        {/* AI PROVIDERS */}
        {activeTab === 'ai' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                NVIDIA NIM (Primary Provider)
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '11px', marginBottom: '8px' }}>
                Connect to NVIDIA's Inference Microservice for high-throughput Llama-3.3 reasoning and Llama-3.2 Vision.
              </div>
              <div style={{ display: 'flex', gap: '6px' }}>
                <input
                  type="password"
                  placeholder="nvapi-..."
                  value={nvidiaKey}
                  onChange={(e) => setNvidiaKey(e.target.value)}
                  style={{
                    flex: 1,
                    backgroundColor: 'var(--bg-tertiary)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                    padding: '6px 8px',
                    fontSize: '11px',
                    color: 'var(--text-primary)'
                  }}
                />
                <button
                  onClick={handleSaveNvidiaKey}
                  style={{
                    backgroundColor: 'var(--accent-primary)',
                    color: '#fff',
                    padding: '6px 12px',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '11px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <Save size={12} /> Save
                </button>
              </div>
            </div>

            <div>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                Default Model
              </div>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                style={{
                  width: '100%',
                  backgroundColor: 'var(--bg-tertiary)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                  padding: '6px 8px',
                  fontSize: '11px',
                  color: 'var(--text-primary)'
                }}
              >
                <option value="meta/llama-3.3-70b-instruct">meta/llama-3.3-70b-instruct (Fast & Accurate)</option>
                <option value="meta/llama-3.2-90b-vision-instruct">meta/llama-3.2-90b-vision-instruct (Vision)</option>
                <option value="meta/llama-3.1-8b-instruct">meta/llama-3.1-8b-instruct (Ultra Fast)</option>
                <option value="gpt-4o">gpt-4o (OpenAI Fallback)</option>
              </select>
            </div>

            <button
              onClick={handleTestConnection}
              disabled={testingConnection}
              style={{
                backgroundColor: 'var(--bg-tertiary)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-primary)',
                padding: '6px 10px',
                borderRadius: 'var(--radius-sm)',
                fontSize: '11px',
                alignSelf: 'flex-start'
              }}
            >
              {testingConnection ? 'Testing...' : 'Test Provider Connection'}
            </button>
          </div>
        )}

        {/* GENERAL SETTINGS */}
        {activeTab === 'general' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
                Appearance & Theme
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  type="button"
                  onClick={() => setTheme('light')}
                  style={{
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: theme === 'light' ? '2px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                    backgroundColor: theme === 'light' ? 'var(--accent-subtle)' : 'var(--bg-tertiary)',
                    color: theme === 'light' ? 'var(--accent-primary)' : 'var(--text-secondary)',
                    fontWeight: theme === 'light' ? 600 : 400
                  }}
                >
                  <Sun size={14} /> Lite (Default)
                </button>
                <button
                  type="button"
                  onClick={() => setTheme('dark')}
                  style={{
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: theme === 'dark' ? '2px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                    backgroundColor: theme === 'dark' ? 'var(--accent-subtle)' : 'var(--bg-tertiary)',
                    color: theme === 'dark' ? 'var(--accent-primary)' : 'var(--text-secondary)',
                    fontWeight: theme === 'dark' ? 600 : 400
                  }}
                >
                  <Moon size={14} /> Dark
                </button>
              </div>
            </div>

            <div>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                Default Search Provider
              </div>
              <select
                value={searchEngine}
                onChange={(e) => setSearchEngine(e.target.value)}
                style={{
                  width: '100%',
                  backgroundColor: 'var(--bg-tertiary)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                  padding: '6px 8px',
                  fontSize: '11px',
                  color: 'var(--text-primary)'
                }}
              >
                <option value="duckduckgo">DuckDuckGo (Privacy Focused)</option>
                <option value="google">Google Search</option>
                <option value="bing">Microsoft Bing</option>
              </select>
            </div>

            <div>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                Startup Behavior
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>
                Automatically restore previous browsing session and tabs.
              </div>
            </div>
          </div>
        )}

        {/* PRIVACY & DATA */}
        {activeTab === 'privacy' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                Local Data Management
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '11px', marginBottom: '8px' }}>
                All history, tabs, and conversation logs are stored exclusively on this PC in SQLite and protected local files.
              </div>
              <button
                onClick={async () => {
                  await clearHistory();
                  setStatusMessage({ text: 'Browsing history cleared.', type: 'success' });
                }}
                style={{
                  backgroundColor: 'rgba(239, 68, 68, 0.15)',
                  color: 'var(--error)',
                  padding: '6px 12px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '11px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  alignSelf: 'flex-start'
                }}
              >
                <Trash2 size={12} /> Clear Browsing History
              </button>
            </div>
          </div>
        )}

        {/* ABOUT */}
        {activeTab === 'about' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
              AI Browser for Windows
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>
              Version 0.1.0 (Production Release Architecture)
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>
              Built with Electron BaseWindow, Chromium, FastAPI, and NVIDIA NIM.
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
