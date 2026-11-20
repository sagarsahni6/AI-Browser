import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Sparkles,
  Bot,
  User,
  ShieldCheck,
  Camera,
  FileText,
  Layers,
  CheckCircle2,
  Square,
  TrendingUp,
  Table,
  Globe,
  Loader2
} from 'lucide-react';
import { useBrowserStore } from '../store/browser-store';

export const AssistantPanel: React.FC = () => {
  const {
    chatMessages,
    lastObservation,
    lastScreenshotUrl,
    activeTab,
    isAgentRunning,
    activeAction,
    sendChatMessage,
    stopAssistant,
    inspectPage,
    capturePage
  } = useBrowserStore();

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [chatMessages, lastObservation, lastScreenshotUrl, activeAction]);

  const handleSend = async () => {
    if (!input.trim() || loading || isAgentRunning) return;
    const text = input;
    setInput('');
    setLoading(true);
    try {
      await sendChatMessage(text);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickSummarize = async () => {
    if (loading || isAgentRunning) return;
    setInput('');
    setLoading(true);
    try {
      await sendChatMessage(`Summarize the current page: ${activeTab?.title || ''} (${activeTab?.url || ''})`);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickTradingView = async () => {
    if (loading || isAgentRunning) return;
    setLoading(true);
    try {
      await sendChatMessage(`Open TradingView (https://www.tradingview.com/chart/?symbol=NVDA) and analyze the NVDA daily chart.`);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickOptionChain = async () => {
    if (loading || isAgentRunning) return;
    setLoading(true);
    try {
      await sendChatMessage(`Extract option chain table data for SPY or current stock and export to CSV.`);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickGoogle = async () => {
    if (loading || isAgentRunning) return;
    setLoading(true);
    try {
      await sendChatMessage(`Open google.com`);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickInspect = async () => {
    setLoading(true);
    try {
      const obs = await inspectPage();
      await sendChatMessage(`I just inspected this page via CDP. Title: "${obs.title}". Found ${obs.interactiveElements.length} interactive elements and ${obs.visibleText.length} characters of visible text.`);
    } catch (e: unknown) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      width: '100%',
      height: '100%',
      backgroundColor: 'var(--bg-secondary)',
      borderLeft: '1px solid var(--border-subtle)',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '10px 14px',
        borderBottom: '1px solid var(--border-subtle)',
        backgroundColor: 'var(--bg-primary)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sparkles size={16} style={{ color: 'var(--accent-primary)' }} />
          <span style={{ fontWeight: 600, fontSize: '13px' }}>AI Autonomous Agent</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {isAgentRunning && (
            <button
              onClick={() => stopAssistant()}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                backgroundColor: '#ef4444',
                color: '#fff',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                padding: '3px 8px',
                fontSize: '11px',
                fontWeight: 600,
                cursor: 'pointer'
              }}
              title="Stop current agent action"
            >
              <Square size={10} fill="#fff" />
              <span>Stop Agent</span>
            </button>
          )}
          <div style={{
            fontSize: '11px',
            color: 'var(--text-secondary)',
            backgroundColor: 'var(--bg-tertiary)',
            padding: '2px 8px',
            borderRadius: 'var(--radius-sm)'
          }}>
            NVIDIA NIM (Multi-Model)
          </div>
        </div>
      </div>

      {/* Active Action Live Banner */}
      {isAgentRunning && activeAction && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '7px 12px',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderBottom: '1px solid rgba(59, 130, 246, 0.2)',
          fontSize: '11.5px',
          color: 'var(--accent-primary)'
        }}>
          <div style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: '#3b82f6',
            boxShadow: '0 0 6px #3b82f6'
          }} />
          <span style={{ fontWeight: 500 }}>
            Executing: <strong>{activeAction.action}</strong>
            {activeAction.parameters?.url ? ` (${activeAction.parameters.url})` : ''}
            {activeAction.parameters?.query ? ` "${activeAction.parameters.query}"` : ''}
            {activeAction.parameters?.question ? ` (${activeAction.parameters.question})` : ''}
          </span>
        </div>
      )}

      {/* Quick Action Chips */}
      <div style={{
        display: 'flex',
        gap: '6px',
        padding: '8px 12px',
        overflowX: 'auto',
        borderBottom: '1px solid var(--border-subtle)',
        backgroundColor: 'var(--bg-secondary)'
      }}>
        <button
          onClick={handleQuickTradingView}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            padding: '4px 8px',
            backgroundColor: 'var(--bg-tertiary)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '11px',
            color: 'var(--text-secondary)',
            whiteSpace: 'nowrap'
          }}
        >
          <TrendingUp size={12} style={{ color: '#10b981' }} />
          <span>TradingView NVDA</span>
        </button>

        <button
          onClick={handleQuickOptionChain}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            padding: '4px 8px',
            backgroundColor: 'var(--bg-tertiary)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '11px',
            color: 'var(--text-secondary)',
            whiteSpace: 'nowrap'
          }}
        >
          <Table size={12} style={{ color: '#f59e0b' }} />
          <span>Option Chain</span>
        </button>

        <button
          onClick={handleQuickGoogle}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            padding: '4px 8px',
            backgroundColor: 'var(--bg-tertiary)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '11px',
            color: 'var(--text-secondary)',
            whiteSpace: 'nowrap'
          }}
        >
          <Globe size={12} style={{ color: '#3b82f6' }} />
          <span>Open Google</span>
        </button>

        <button
          onClick={handleQuickSummarize}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            padding: '4px 8px',
            backgroundColor: 'var(--bg-tertiary)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '11px',
            color: 'var(--text-secondary)',
            whiteSpace: 'nowrap'
          }}
        >
          <FileText size={12} />
          <span>Summarize Page</span>
        </button>

        <button
          onClick={handleQuickInspect}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            padding: '4px 8px',
            backgroundColor: 'var(--bg-tertiary)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '11px',
            color: 'var(--text-secondary)',
            whiteSpace: 'nowrap'
          }}
        >
          <ShieldCheck size={12} />
          <span>Inspect CDP</span>
        </button>

        <button
          onClick={() => capturePage()}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            padding: '4px 8px',
            backgroundColor: 'var(--bg-tertiary)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '11px',
            color: 'var(--text-secondary)',
            whiteSpace: 'nowrap'
          }}
        >
          <Camera size={12} />
          <span>Screenshot</span>
        </button>
      </div>

      {/* Messages Scroll Area */}
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}
      >
        {chatMessages.map(msg => (
          <div
            key={msg.id}
            style={{
              display: 'flex',
              gap: '8px',
              flexDirection: msg.sender === 'user' ? 'row-reverse' : 'row'
            }}
          >
            <div style={{
              width: '24px',
              height: '24px',
              borderRadius: '50%',
              backgroundColor: msg.sender === 'user' ? 'var(--accent-primary)' : 'var(--bg-hover)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}>
              {msg.sender === 'user' ? <User size={12} /> : <Bot size={12} />}
            </div>

            <div style={{
              maxWidth: '85%',
              padding: '8px 12px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: msg.sender === 'user' ? 'var(--accent-primary)' : 'var(--bg-tertiary)',
              color: msg.sender === 'user' ? '#fff' : 'var(--text-primary)',
              fontSize: '12.5px',
              lineHeight: 1.5,
              wordBreak: 'break-word',
              whiteSpace: 'pre-wrap'
            }}>
              {msg.content}
            </div>
          </div>
        ))}

        {/* Live Observation Card if available */}
        {lastObservation && (
          <div style={{
            backgroundColor: 'var(--bg-tertiary)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            padding: '10px',
            fontSize: '11.5px',
            marginTop: '4px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--success)', marginBottom: '6px' }}>
              <CheckCircle2 size={13} />
              <span style={{ fontWeight: 600 }}>CDP Observation Attached</span>
            </div>
            <div style={{ color: 'var(--text-secondary)' }}>
              <div><strong>URL:</strong> {lastObservation.url}</div>
              <div><strong>Viewport:</strong> {lastObservation.viewport.width} x {lastObservation.viewport.height}</div>
              <div><strong>Elements:</strong> {lastObservation.interactiveElements.length} interactive</div>
              <div><strong>Text snippet:</strong> {lastObservation.visibleText.slice(0, 120)}...</div>
            </div>
          </div>
        )}

        {/* Screenshot preview if available */}
        {lastScreenshotUrl && (
          <div style={{
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            overflow: 'hidden',
            backgroundColor: '#000',
            marginTop: '4px'
          }}>
            <img
              src={lastScreenshotUrl}
              alt="Screenshot Preview"
              style={{ width: '100%', height: 'auto', display: 'block' }}
            />
          </div>
        )}
      </div>

      {/* Input area */}
      <div style={{
        padding: '10px 12px',
        borderTop: '1px solid var(--border-subtle)',
        backgroundColor: 'var(--bg-primary)'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          backgroundColor: 'var(--bg-secondary)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-subtle)',
          padding: '4px 8px 4px 12px',
          gap: '8px'
        }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSend();
            }}
            placeholder="Ask AI about this page or task..."
            style={{
              flex: 1,
              fontSize: '12px',
              color: 'var(--text-primary)'
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            style={{
              padding: '6px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: input.trim() && !loading ? 'var(--accent-primary)' : 'transparent',
              color: input.trim() && !loading ? '#fff' : 'var(--text-muted)'
            }}
          >
            <Send size={14} />
          </button>
        </div>
      </div>
    </div>
  );
};
