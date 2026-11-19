import React, { useState } from 'react';
import {
  Sparkles,
  ShieldCheck,
  Search,
  Cpu,
  Key,
  CheckCircle,
  ArrowRight,
  ArrowLeft
} from 'lucide-react';

export const FirstRunWizard: React.FC<{ onComplete: () => void }> = ({ onComplete }) => {
  const [step, setStep] = useState(1);
  const [nvidiaKey, setNvidiaKey] = useState('');
  const [searchEngine, setSearchEngine] = useState('duckduckgo');
  const [model, setModel] = useState('meta/llama-3.3-70b-instruct');

  const handleFinish = async () => {
    if (nvidiaKey.trim() && window.electronAPI?.setSecret) {
      await window.electronAPI.setSecret('NVIDIA_API_KEY', nvidiaKey.trim());
    }
    localStorage.setItem('has_completed_onboarding', 'true');
    onComplete();
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      height: '100vh',
      backgroundColor: 'rgba(0, 0, 0, 0.85)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 10000,
      fontFamily: 'var(--font-sans)',
      userSelect: 'none'
    }}>
      <div style={{
        width: '520px',
        backgroundColor: 'var(--bg-secondary)',
        border: '1px solid var(--border-strong)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--shadow-lg)',
        padding: '28px',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px'
      }}>
        {/* Step Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              width: '28px',
              height: '28px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--accent-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontWeight: 'bold',
              fontSize: '13px'
            }}>
              AI
            </div>
            <span style={{ fontWeight: 600, fontSize: '15px' }}>First-Run Setup</span>
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Step {step} of 5</span>
        </div>

        {/* Step 1: Welcome */}
        {step === 1 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 600 }}>Welcome to AI Browser</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '13px', lineHeight: 1.6 }}>
              A real Chromium desktop browser combined with an autonomous AI intelligence system capable of webpage understanding, cited research, and multi-step tasks.
            </p>
            <div style={{
              backgroundColor: 'var(--bg-tertiary)',
              padding: '12px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
              fontSize: '12px',
              color: 'var(--text-secondary)',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px'
            }}>
              <div>✓ Native Chromium multi-tab browsing</div>
              <div>✓ In-page DOM & visual automation via controlled CDP</div>
              <div>✓ Multi-provider AI powered by NVIDIA NIM</div>
              <div>✓ 100% local SQLite storage & DPAPI encrypted secrets</div>
            </div>
          </div>
        )}

        {/* Step 2: Search Engine */}
        {step === 2 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 600 }}>Choose Default Search Engine</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
              Select the search engine used for address bar queries and native research.
            </p>
            {['duckduckgo', 'google', 'bing'].map(engine => (
              <label
                key={engine}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '10px 12px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: searchEngine === engine ? 'var(--bg-hover)' : 'var(--bg-tertiary)',
                  cursor: 'pointer',
                  border: searchEngine === engine ? '1px solid var(--accent-primary)' : '1px solid transparent',
                  textTransform: 'capitalize',
                  fontSize: '13px'
                }}
              >
                <input
                  type="radio"
                  name="search"
                  checked={searchEngine === engine}
                  onChange={() => setSearchEngine(engine)}
                />
                <span>{engine === 'duckduckgo' ? 'DuckDuckGo (Privacy Focused)' : engine}</span>
              </label>
            ))}
          </div>
        )}

        {/* Step 3: NVIDIA NIM API Key */}
        {step === 3 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 600 }}>Configure NVIDIA NIM (Optional)</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '12px', lineHeight: 1.5 }}>
              Enter your NVIDIA API key to activate cloud inference with <strong>meta/llama-3.3-70b-instruct</strong> and multimodal vision.
            </p>
            <input
              type="password"
              placeholder="nvapi-..."
              value={nvidiaKey}
              onChange={(e) => setNvidiaKey(e.target.value)}
              style={{
                backgroundColor: 'var(--bg-tertiary)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
                padding: '10px 12px',
                fontSize: '13px',
                color: 'var(--text-primary)'
              }}
            />
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Note: You can skip this step and configure keys anytime in Settings.
            </div>
          </div>
        )}

        {/* Step 4: Model Selection */}
        {step === 4 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 600 }}>Default Intelligence Model</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
              Choose your primary reasoning and tool-execution model.
            </p>
            {[
              { id: 'meta/llama-3.3-70b-instruct', label: 'meta/llama-3.3-70b-instruct (Recommended)', desc: 'High reasoning, tool calling, 128k context' },
              { id: 'meta/llama-3.2-90b-vision-instruct', label: 'meta/llama-3.2-90b-vision-instruct', desc: 'Multimodal vision specialist' },
              { id: 'meta/llama-3.1-8b-instruct', label: 'meta/llama-3.1-8b-instruct', desc: 'Ultra-fast low latency responses' },
            ].map(m => (
              <label
                key={m.id}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  padding: '10px 12px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: model === m.id ? 'var(--bg-hover)' : 'var(--bg-tertiary)',
                  cursor: 'pointer',
                  border: model === m.id ? '1px solid var(--accent-primary)' : '1px solid transparent'
                }}
              >
                <input
                  type="radio"
                  name="model"
                  checked={model === m.id}
                  onChange={() => setModel(m.id)}
                  style={{ marginTop: '3px' }}
                />
                <div>
                  <div style={{ fontSize: '12.5px', fontWeight: 500 }}>{m.label}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{m.desc}</div>
                </div>
              </label>
            ))}
          </div>
        )}

        {/* Step 5: Privacy Confirmation */}
        {step === 5 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 600 }}>Local Privacy & Safety</h2>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center', color: 'var(--success)' }}>
              <ShieldCheck size={28} />
              <div style={{ fontWeight: 600, fontSize: '13px' }}>Your Data Remains Yours</div>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '12px', lineHeight: 1.6 }}>
              AI Browser stores your history, bookmarks, task traces, and memories locally in SQLite. Webpages you visit cannot inspect your conversations, and sensitive password fields are automatically masked.
            </p>
          </div>
        )}

        {/* Buttons Footer */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '12px' }}>
          {step > 1 ? (
            <button
              onClick={() => setStep(step - 1)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--bg-tertiary)',
                color: 'var(--text-secondary)',
                fontSize: '12px'
              }}
            >
              <ArrowLeft size={14} /> Back
            </button>
          ) : <div />}

          {step < 5 ? (
            <button
              onClick={() => setStep(step + 1)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 18px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--accent-primary)',
                color: '#fff',
                fontSize: '12px',
                fontWeight: 500
              }}
            >
              Continue <ArrowRight size={14} />
            </button>
          ) : (
            <button
              onClick={handleFinish}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 20px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--success)',
                color: '#fff',
                fontSize: '12px',
                fontWeight: 600
              }}
            >
              <CheckCircle size={14} /> Start Browsing
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
