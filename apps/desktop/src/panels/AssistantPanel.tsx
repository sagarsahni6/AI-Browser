import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Sparkles,
  ShieldCheck,
  Camera,
  FileText,
  CheckCircle2,
  Square,
  TrendingUp,
  Table,
  Globe,
  RotateCcw,
  Cpu
} from 'lucide-react';
import { useBrowserStore } from '../store/browser-store';
import { ChatMessageItem } from '../components/chat/ChatMessage';
import { ApprovalDialog } from '../components/ApprovalDialog';
import styles from './AssistantPanel.module.css';

const PROVIDER_OPTIONS = [
  { id: 'browser_use_cloud', label: 'Browser Use Cloud (bu-4.0)' },
  { id: 'nvidia_nim', label: 'NVIDIA NIM' },
  { id: 'openai_compatible', label: 'OpenAI Compatible' },
  { id: 'anthropic', label: 'Anthropic Claude' },
  { id: 'google_gemini', label: 'Google Gemini' },
  { id: 'groq', label: 'Groq (Ultra-Fast)' },
  { id: 'ollama', label: 'Ollama (Local)' },
];

export const AssistantPanel: React.FC = () => {
  const {
    chatMessages,
    lastObservation,
    lastScreenshotUrl,
    activeTab,
    isAgentRunning,
    activeAction,
    setActiveAction,
    sendChatMessage,
    stopAssistant,
    inspectPage,
    capturePage
  } = useBrowserStore();

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState('nvidia_nim');
  const [showTrace, setShowTrace] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [chatMessages, lastObservation, lastScreenshotUrl, activeAction]);

  useEffect(() => {
    const unsubPrompt = window.electronAPI?.onChatIncomingPrompt?.((prompt: string) => {
      if (prompt) {
        setInput(prompt);
        if (textareaRef.current) {
          textareaRef.current.focus();
        }
      }
    });
    return () => unsubPrompt?.();
  }, []);

  const handleSend = async () => {
    if (!input.trim() || loading || isAgentRunning) return;
    const text = input;
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    setLoading(true);
    try {
      await sendChatMessage(text, { provider: selectedProvider });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  };

  const handleClearChat = () => {
    useBrowserStore.setState({
      chatMessages: [
        {
          id: `welcome-${Date.now()}`,
          sender: 'assistant',
          content: 'Started new conversation. I can inspect pages, capture screenshots, summarize content, or conduct autonomous browser tasks.',
          timestamp: Date.now()
        }
      ],
      lastObservation: null,
      lastScreenshotUrl: null
    });
  };

  const handleQuickSummarize = async () => {
    if (loading || isAgentRunning) return;
    setLoading(true);
    try {
      await sendChatMessage(`Summarize the current page: ${activeTab?.title || ''} (${activeTab?.url || ''})`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeepResearch = async () => {
    if (loading || isAgentRunning) return;
    setLoading(true);
    try {
      await sendChatMessage(`Perform deep web research on: ${activeTab?.title || 'current topic'} and provide a cited comparison`, { provider: selectedProvider });
    } finally {
      setLoading(false);
    }
  };

  const handleQuickTableExtraction = async () => {
    if (loading || isAgentRunning) return;
    setLoading(true);
    try {
      await sendChatMessage(`Extract all structured table and product records from this page and prepare export`, { provider: selectedProvider });
    } finally {
      setLoading(false);
    }
  };

  const handleQuickCompare = async () => {
    if (loading || isAgentRunning) return;
    setLoading(true);
    try {
      await sendChatMessage(`Compare the top options, specifications, prices, and pros/cons for this topic`, { provider: selectedProvider });
    } finally {
      setLoading(false);
    }
  };

  const handleCompareTabs = async () => {
    if (loading || isAgentRunning) return;
    setLoading(true);
    try {
      await sendChatMessage(`Compare and synthesize content across all open browser tabs. Identify key differences, common themes, and provide a structured comparison with citations.`, { provider: selectedProvider });
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
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <Sparkles size={16} style={{ color: 'var(--accent-primary)' }} />
          <span className={styles.headerTitle}>AI Autonomous Agent</span>
          {isAgentRunning 
            ? <span className={styles.modeBadge} style={{background:'#f59e0b'}}>MODE B: ACTION</span>
            : <span className={styles.modeBadge} style={{background:'#10b981'}}>MODE A: RESEARCH</span>
          }
        </div>

        <div className={styles.headerRight}>
          {isAgentRunning && (
            <button
              onClick={() => stopAssistant()}
              className={styles.stopBtn}
              title="Stop current agent action"
            >
              <Square size={10} fill="#fff" />
              <span>Stop Agent</span>
            </button>
          )}

          {/* Provider Selector Dropdown */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Cpu size={12} style={{ color: 'var(--text-muted)' }} />
            <select
              value={selectedProvider}
              onChange={(e) => setSelectedProvider(e.target.value)}
              className={styles.badge}
              style={{ cursor: 'pointer', outline: 'none' }}
              title="Select Active AI Provider"
            >
              {PROVIDER_OPTIONS.map(p => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
          </div>

          <button
            onClick={handleClearChat}
            className="icon-btn"
            style={{ width: '24px', height: '24px' }}
            title="Start New Conversation"
          >
            <RotateCcw size={12} />
          </button>
        </div>
      </div>

      {/* Active Action Live Banner */}
      {isAgentRunning && activeAction && activeAction.status !== 'approval_required' && (
        <div className={`${styles.activeActionBanner} animate-slide-in-down`}>
          <div className={styles.pulseDot} />
          <span style={{ fontWeight: 500 }}>
            Running Step {activeAction.step_number || '?'}/{activeAction.total_steps || '?'}: <strong>{activeAction.action}</strong>
            {activeAction.parameters?.url ? ` (${activeAction.parameters.url})` : ''}
            {activeAction.parameters?.query ? ` "${activeAction.parameters.query}"` : ''}
            {activeAction.parameters?.question ? ` (${activeAction.parameters.question})` : ''}
          </span>
        </div>
      )}

      {/* ReAct Thought/Plan Trace */}
      {isAgentRunning && activeAction?.thought && (
        <div className={styles.reactTrace}>
          <div className={styles.reactTraceHeader} onClick={() => setShowTrace(t => !t)}>
            <span>🧠 Agent Reasoning</span>
            <span>{showTrace ? '▲' : '▼'}</span>
          </div>
          {showTrace && (
            <div className={styles.reactTraceBody}>
              <pre className={styles.reactThought}>{activeAction.thought}</pre>
              {activeAction.plan && (
                <div className={styles.reactPlan}>
                  <strong>Plan:</strong>
                  <pre>{activeAction.plan}</pre>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Sensitive Action Approval Dialog */}
      <ApprovalDialog
        isOpen={Boolean(activeAction && activeAction.status === 'approval_required')}
        actionTitle="Agent Requests Authorization"
        reason={activeAction?.result?.includes('RED TIER') ? `🔴 RED TIER — ${activeAction.result}` : (activeAction?.result || 'The autonomous agent is requesting permission to execute an action requiring user approval.')}
        toolName={activeAction?.action}
        parameters={activeAction?.parameters}
        onApprove={() => {
          if (activeAction?.parameters?.task_id && window.electronAPI?.approveTask) {
            window.electronAPI.approveTask(activeAction.parameters.task_id, true);
          }
          setActiveAction(null);
        }}
        onReject={() => {
          if (activeAction?.parameters?.task_id && window.electronAPI?.rejectTask) {
            window.electronAPI.rejectTask(activeAction.parameters.task_id);
          }
          setActiveAction(null);
          stopAssistant();
        }}
      />

      {/* Quick Action Chips */}
      <div className={styles.quickChips}>
        <button onClick={handleDeepResearch} className={styles.chipBtn}>
          <Sparkles size={12} style={{ color: 'var(--accent-primary)' }} />
          <span>🔍 Deep Research</span>
        </button>

        <button onClick={handleCompareTabs} className={styles.chipBtn}>
          <Globe size={12} style={{ color: '#8b5cf6' }} />
          <span>⚖️ Compare Tabs</span>
        </button>

        <button onClick={handleQuickCompare} className={styles.chipBtn}>
          <TrendingUp size={12} style={{ color: '#10b981' }} />
          <span>Compare Options</span>
        </button>

        <button onClick={handleQuickTableExtraction} className={styles.chipBtn}>
          <Table size={12} style={{ color: '#f59e0b' }} />
          <span>📊 Extract Table / CSV</span>
        </button>

        <button onClick={handleQuickSummarize} className={styles.chipBtn}>
          <FileText size={12} />
          <span>⚡ Summarize Page</span>
        </button>

        <button onClick={handleQuickInspect} className={styles.chipBtn}>
          <ShieldCheck size={12} />
          <span>Inspect CDP</span>
        </button>

        <button onClick={() => capturePage()} className={styles.chipBtn}>
          <Camera size={12} />
          <span>Screenshot</span>
        </button>
      </div>

      {/* Messages Scroll Area */}
      <div ref={scrollRef} className={styles.chatList}>
        {chatMessages.map(msg => (
          <ChatMessageItem
            key={msg.id}
            id={msg.id}
            sender={msg.sender}
            content={msg.content}
            timestamp={msg.timestamp}
            metadata={msg.metadata as any}
          />
        ))}

        {/* Live Observation Card if available */}
        {lastObservation && (
          <div className={`${styles.observationCard} animate-fade-in`}>
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
          <div className={`${styles.screenshotPreview} animate-fade-in`}>
            <img
              src={lastScreenshotUrl}
              alt="Screenshot Preview"
              className={styles.screenshotImg}
            />
          </div>
        )}
      </div>

      {/* Input area */}
      <div className={styles.inputArea}>
        <div className={styles.inputWrapper}>
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask AI or delegate a task (Enter to send, Shift+Enter for new line)..."
            style={{
              flex: 1,
              fontSize: '12px',
              color: 'var(--text-primary)',
              resize: 'none',
              maxHeight: '120px',
              lineHeight: '1.4'
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className={styles.sendBtn}
            style={{
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
