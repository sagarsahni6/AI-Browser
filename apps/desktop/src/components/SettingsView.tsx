import React, { useState, useEffect } from 'react';
import {
  Shield,
  Key,
  Cpu,
  CheckCircle,
  AlertCircle,
  Trash2,
  Save,
  Globe,
  Sliders,
  Sun,
  Moon,
  Sparkles
} from 'lucide-react';
import { useBrowserStore } from '../store/browser-store';

interface ProviderConfig {
  id: string;
  name: string;
  keyName: string;
  defaultModel: string;
  models: string[];
  requiresKey: boolean;
  helpText: string;
}

const PROVIDERS: ProviderConfig[] = [
  {
    id: 'browser_use_cloud',
    name: 'Browser Use Cloud',
    keyName: 'BROWSER_USE_API_KEY',
    defaultModel: 'bu-4.0',
    models: [
      'bu-4.0',
      'bu-4.0-pro'
    ],
    requiresKey: true,
    helpText: 'Official Browser Use Cloud gateway with hosted stealth browsers and bu-4.0.'
  },
  {
    id: 'nvidia_nim',
    name: 'NVIDIA NIM (Primary)',
    keyName: 'NVIDIA_API_KEY',
    defaultModel: 'nvidia/nemotron-3.5-lightning-30b-a3b',
    models: [
      'nvidia/nemotron-3.5-lightning-30b-a3b',
      'nvidia/nemotron-3.5-super-vl-120b-a12b',
      'mistralai/mistral-large-4-1t-a52b',
      'meta/llama-3.3-70b-instruct'
    ],
    requiresKey: true,
    helpText: 'High-throughput reasoning and multimodal vision powered by NVIDIA microservices.'
  },
  {
    id: 'anthropic',
    name: 'Anthropic Claude',
    keyName: 'ANTHROPIC_API_KEY',
    defaultModel: 'claude-3-5-sonnet-20241022',
    models: [
      'claude-3-5-sonnet-20241022',
      'claude-3-5-haiku-20241022',
      'claude-3-opus-20240229'
    ],
    requiresKey: true,
    helpText: 'Anthropic Claude Messages API with deep instruction following and safety.'
  },
  {
    id: 'google_gemini',
    name: 'Google Gemini',
    keyName: 'GOOGLE_API_KEY',
    defaultModel: 'gemini-2.0-flash',
    models: [
      'gemini-2.0-flash',
      'gemini-1.5-pro',
      'gemini-2.0-pro-exp'
    ],
    requiresKey: true,
    helpText: 'Ultra-fast multimodal Gemini with up to 1M token context.'
  },
  {
    id: 'groq',
    name: 'Groq (Ultra-Fast)',
    keyName: 'GROQ_API_KEY',
    defaultModel: 'llama-3.3-70b-versatile',
    models: [
      'llama-3.3-70b-versatile',
      'llama-3.1-8b-instant',
      'mixtral-8x7b-32768'
    ],
    requiresKey: true,
    helpText: 'Sub-second LPU inference for instantaneous browser interactions.'
  },
  {
    id: 'openai_compatible',
    name: 'OpenAI Compatible',
    keyName: 'OPENAI_API_KEY',
    defaultModel: 'gpt-4o',
    models: [
      'gpt-4o',
      'gpt-4o-mini',
      'o1-preview'
    ],
    requiresKey: true,
    helpText: 'Standard OpenAI-compatible completions endpoint.'
  },
  {
    id: 'ollama',
    name: 'Ollama (Local Offline)',
    keyName: 'OLLAMA_BASE_URL',
    defaultModel: 'llama3.2',
    models: [
      'llama3.2',
      'mistral',
      'qwen2.5',
      'llava'
    ],
    requiresKey: false,
    helpText: '100% private local inference running on localhost:11434. No API key needed.'
  }
];

export const SettingsView: React.FC = () => {
  const { clearHistory, theme, setTheme } = useBrowserStore();

  const [activeTab, setActiveTab] = useState<'general' | 'ai' | 'privacy' | 'about' | 'memory' | 'monitors'>('ai');
  const [selectedProviderId, setSelectedProviderId] = useState('nvidia_nim');
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({
    NVIDIA_API_KEY: '',
    ANTHROPIC_API_KEY: '',
    GOOGLE_API_KEY: '',
    GROQ_API_KEY: '',
    OPENAI_API_KEY: '',
    OLLAMA_BASE_URL: 'http://localhost:11434'
  });
  const [selectedModel, setSelectedModel] = useState('nvidia/nemotron-3.5-lightning-30b-a3b');
  const [searchEngine, setSearchEngine] = useState('duckduckgo');
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
  const [testingConnection, setTestingConnection] = useState(false);

  // Memory & Monitors state
  const [memories, setMemories] = useState<any[]>([]);
  const [newMemKey, setNewMemKey] = useState('');
  const [newMemVal, setNewMemVal] = useState('');
  const [monitors, setMonitors] = useState<any[]>([]);
  const [newMonName, setNewMonName] = useState('');
  const [newMonUrl, setNewMonUrl] = useState('');

  const loadMemories = async () => {
    if (window.electronAPI?.getAllMemories) {
      try {
        const list = await window.electronAPI.getAllMemories();
        setMemories(list || []);
      } catch (err) {
        console.error('Failed to load memories:', err);
      }
    }
  };

  const loadMonitors = async () => {
    if (window.electronAPI?.listMonitors) {
      try {
        const list = await window.electronAPI.listMonitors();
        setMonitors(list || []);
      } catch (err) {
        console.error('Failed to load monitors:', err);
      }
    }
  };

  useEffect(() => {
    if (activeTab === 'memory') loadMemories();
    if (activeTab === 'monitors') loadMonitors();
  }, [activeTab]);

  const curProvider = PROVIDERS.find(p => p.id === selectedProviderId) || PROVIDERS[0];

  useEffect(() => {
    if (window.electronAPI?.getSecret) {
      for (const p of PROVIDERS) {
        window.electronAPI.getSecret(p.keyName).then(key => {
          if (key) {
            setApiKeys(prev => ({ ...prev, [p.keyName]: key }));
          }
        });
      }
    }
  }, []);

  const handleSaveKey = async () => {
    if (window.electronAPI?.setSecret) {
      const val = apiKeys[curProvider.keyName] || '';
      await window.electronAPI.setSecret(curProvider.keyName, val);
      setStatusMessage({ text: `${curProvider.name} credentials saved securely.`, type: 'success' });
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
          provider_id: curProvider.id,
          api_key: apiKeys[curProvider.keyName]
        })
      });
      const data = await res.json();
      if (data.success) {
        setStatusMessage({ text: data.message || `Connected to ${curProvider.name}!`, type: 'success' });
      } else {
        setStatusMessage({ text: `Connection test: ${data.message}`, type: 'error' });
      }
    } catch (err: any) {
      setStatusMessage({ text: `Backend unreachable: ${err.message}`, type: 'error' });
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
          { id: 'memory' as const, label: 'Memory & Context', icon: Sparkles },
          { id: 'monitors' as const, label: 'Web Monitors', icon: Globe },
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
                Select AI Provider
              </div>
              <select
                value={selectedProviderId}
                onChange={(e) => {
                  const pid = e.target.value;
                  setSelectedProviderId(pid);
                  const p = PROVIDERS.find(x => x.id === pid);
                  if (p) setSelectedModel(p.defaultModel);
                }}
                style={{
                  width: '100%',
                  backgroundColor: 'var(--bg-tertiary)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                  padding: '6px 8px',
                  fontSize: '11px',
                  color: 'var(--text-primary)',
                  fontWeight: 500
                }}
              >
                {PROVIDERS.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
              <div style={{ color: 'var(--text-secondary)', fontSize: '11px', marginTop: '4px' }}>
                {curProvider.helpText}
              </div>
            </div>

            {curProvider.requiresKey ? (
              <div>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                  {curProvider.name} API Key
                </div>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <input
                    type="password"
                    placeholder="Enter API Key..."
                    value={apiKeys[curProvider.keyName] || ''}
                    onChange={(e) => setApiKeys({ ...apiKeys, [curProvider.keyName]: e.target.value })}
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
                    onClick={handleSaveKey}
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
            ) : (
              <div>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                  Ollama Base Endpoint
                </div>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <input
                    type="text"
                    value={apiKeys.OLLAMA_BASE_URL || 'http://localhost:11434'}
                    onChange={(e) => setApiKeys({ ...apiKeys, OLLAMA_BASE_URL: e.target.value })}
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
                    onClick={handleSaveKey}
                    style={{
                      backgroundColor: 'var(--accent-primary)',
                      color: '#fff',
                      padding: '6px 12px',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '11px'
                    }}
                  >
                    Save
                  </button>
                </div>
              </div>
            )}

            <div>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                Model Selection
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
                {curProvider.models.map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
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
              {testingConnection ? 'Testing...' : `Test ${curProvider.name} Connection`}
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
        {activeTab === 'memory' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
              Persistent AI Memory & Context
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>
              Preferences and context saved here are automatically injected into AI prompts across browsing sessions.
            </div>

            {/* Add Memory Form */}
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                if (!newMemKey.trim() || !newMemVal.trim() || !window.electronAPI?.remember) return;
                await window.electronAPI.remember({ key: newMemKey.trim(), value: newMemVal.trim() });
                setNewMemKey('');
                setNewMemVal('');
                loadMemories();
                setStatusMessage({ text: 'Memory saved!', type: 'success' });
              }}
              style={{
                display: 'flex',
                gap: '6px',
                padding: '8px',
                backgroundColor: 'var(--bg-tertiary)',
                borderRadius: 'var(--radius-sm)'
              }}
            >
              <input
                type="text"
                placeholder="Key (e.g. favorite_export)"
                value={newMemKey}
                onChange={(e) => setNewMemKey(e.target.value)}
                style={{
                  flex: 1,
                  padding: '5px 8px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  fontSize: '11px'
                }}
                required
              />
              <input
                type="text"
                placeholder="Value (e.g. CSV with quotes)"
                value={newMemVal}
                onChange={(e) => setNewMemVal(e.target.value)}
                style={{
                  flex: 2,
                  padding: '5px 8px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  fontSize: '11px'
                }}
                required
              />
              <button
                type="submit"
                style={{
                  padding: '5px 12px',
                  backgroundColor: 'var(--accent-primary)',
                  color: '#fff',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                Save
              </button>
            </form>

            {/* Memories List */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {memories.length === 0 ? (
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>No memories saved yet.</div>
              ) : (
                memories.map((m) => (
                  <div
                    key={m.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '6px 10px',
                      backgroundColor: 'var(--bg-tertiary)',
                      borderRadius: 'var(--radius-sm)'
                    }}
                  >
                    <div>
                      <span style={{ fontWeight: 600, color: 'var(--accent-primary)', marginRight: '6px' }}>{m.key}:</span>
                      <span style={{ color: 'var(--text-secondary)' }}>{m.value}</span>
                    </div>
                    <button
                      onClick={async () => {
                        if (window.electronAPI?.forgetMemory) {
                          await window.electronAPI.forgetMemory(m.id);
                          loadMemories();
                        }
                      }}
                      style={{ color: 'var(--text-muted)', background: 'transparent', border: 'none', cursor: 'pointer' }}
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* WEBSITE MONITORS */}
        {activeTab === 'monitors' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
              Scheduled Website Monitors
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>
              Tracks webpages and alerts you when content changes occur.
            </div>

            {/* Add Monitor Form */}
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                if (!newMonName.trim() || !newMonUrl.trim() || !window.electronAPI?.createMonitor) return;
                await window.electronAPI.createMonitor({ name: newMonName.trim(), url: newMonUrl.trim() });
                setNewMonName('');
                setNewMonUrl('');
                loadMonitors();
                setStatusMessage({ text: 'Monitor created and baseline established!', type: 'success' });
              }}
              style={{
                display: 'flex',
                gap: '6px',
                padding: '8px',
                backgroundColor: 'var(--bg-tertiary)',
                borderRadius: 'var(--radius-sm)'
              }}
            >
              <input
                type="text"
                placeholder="Name (e.g. Stock Alert)"
                value={newMonName}
                onChange={(e) => setNewMonName(e.target.value)}
                style={{
                  flex: 1,
                  padding: '5px 8px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  fontSize: '11px'
                }}
                required
              />
              <input
                type="url"
                placeholder="https://example.com/item"
                value={newMonUrl}
                onChange={(e) => setNewMonUrl(e.target.value)}
                style={{
                  flex: 2,
                  padding: '5px 8px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  fontSize: '11px'
                }}
                required
              />
              <button
                type="submit"
                style={{
                  padding: '5px 12px',
                  backgroundColor: 'var(--accent-primary)',
                  color: '#fff',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                Add Monitor
              </button>
            </form>

            {/* Monitors List */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {monitors.length === 0 ? (
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>No website monitors active.</div>
              ) : (
                monitors.map((mon) => (
                  <div
                    key={mon.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '8px 10px',
                      backgroundColor: 'var(--bg-tertiary)',
                      borderRadius: 'var(--radius-sm)'
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{mon.name}</div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{mon.url}</div>
                      <div style={{ fontSize: '9.5px', color: mon.status === 'alert' ? 'var(--error)' : 'var(--success)' }}>
                        Status: {mon.status} &bull; Last check: {mon.last_check_at ? new Date(mon.last_check_at * 1000).toLocaleTimeString() : 'Never'}
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '4px' }}>
                      <button
                        onClick={async () => {
                          if (window.electronAPI?.checkMonitorNow) {
                            const res = await window.electronAPI.checkMonitorNow(mon.id);
                            loadMonitors();
                            setStatusMessage({
                              text: res.changed ? 'Change detected on website!' : 'No changes detected.',
                              type: res.changed ? 'error' : 'success'
                            });
                          }
                        }}
                        style={{
                          fontSize: '10px',
                          padding: '3px 6px',
                          borderRadius: 'var(--radius-sm)',
                          backgroundColor: 'var(--bg-hover)',
                          color: 'var(--text-primary)',
                          border: 'none',
                          cursor: 'pointer'
                        }}
                      >
                        Check Now
                      </button>
                      <button
                        onClick={async () => {
                          if (window.electronAPI?.deleteMonitor) {
                            await window.electronAPI.deleteMonitor(mon.id);
                            loadMonitors();
                          }
                        }}
                        style={{ color: 'var(--text-muted)', background: 'transparent', border: 'none', cursor: 'pointer' }}
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                ))
              )}
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
              Version 0.2.0 (Fully Agentic Multi-Model Release)
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>
              Built with Electron BaseWindow, Chromium, FastAPI, and Universal AI Providers (NVIDIA, Claude, Gemini, Groq, Ollama).
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
