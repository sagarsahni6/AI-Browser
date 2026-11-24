import React, { useState, useRef, useEffect, useMemo } from 'react';
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
  Cpu,
  Search,
  Download,
  Clock,
  X,
  Layers,
  Check,
  ChevronDown
} from 'lucide-react';
import { useBrowserStore } from '../store/browser-store';
import { ChatMessageItem } from '../components/chat/ChatMessage';
import { ApprovalDialog } from '../components/ApprovalDialog';
import { ProgressBanner } from '../components/ProgressBanner';
import styles from './AssistantPanel.module.css';

const PROVIDER_OPTIONS = [
  { id: 'nvidia_nim', label: 'NVIDIA NIM' },
  { id: 'browser_use_cloud', label: 'Browser Use Cloud (bu-4.0)' },
  { id: 'openai_compatible', label: 'OpenAI Compatible' },
  { id: 'anthropic', label: 'Anthropic Claude' },
  { id: 'google_gemini', label: 'Google Gemini' },
  { id: 'groq', label: 'Groq (Ultra-Fast)' },
  { id: 'ollama', label: 'Ollama (Local)' },
];

const ENGINE_OPTIONS = [
  { id: 'langgraph', label: 'LangGraph Multi-Agent' },
  { id: 'browser_use', label: 'Browser-Use Cloud' },
  { id: 'native', label: 'Ambient Co-Pilot' }
];

type ChipCategory = 'research' | 'automation' | 'inspect';

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
  const [selectedEngine, setSelectedEngine] = useState('langgraph');
  const [showTrace, setShowTrace] = useState(false);
  const [activeCategory, setActiveCategory] = useState<ChipCategory>('research');

  // Search & Filter state
  const [showSearch, setShowSearch] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Context inclusion toggles
  const [includeContext, setIncludeContext] = useState(true);
  const [attachScreenshot, setAttachScreenshot] = useState(false);

  // Prompt History
  const [promptHistory, setPromptHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState<number>(-1);

  // Live Timer
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Export Toast state
  const [exportNotice, setExportNotice] = useState<string | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll on new messages or action updates
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [chatMessages, lastObservation, lastScreenshotUrl, activeAction]);

  // Live Elapsed Timer when agent is running
  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    if (isAgentRunning) {
      setElapsedSeconds(0);
      timer = setInterval(() => {
        setElapsedSeconds(s => s + 1);
      }, 1000);
    } else {
      setElapsedSeconds(0);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isAgentRunning]);

  // Incoming prompt listener (from context menus, ask AI, etc.)
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

    // Save prompt to history
    setPromptHistory(prev => [text, ...prev.filter(p => p !== text)].slice(0, 30));
    setHistoryIndex(-1);

    setLoading(true);
    try {
      let contextPayload: Record<string, unknown> = {
        provider: selectedProvider,
        engine: selectedEngine,
        includeContext,
      };

      if (attachScreenshot && capturePage) {
        try {
          const shot = await capturePage();
          if (shot) {
            contextPayload.screenshot = shot;
          }
        } catch {
          // ignore transient capture failure
        }
      }

      await sendChatMessage(text, contextPayload);
    } catch (err) {
      console.error('[AssistantPanel] sendChatMessage error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
      return;
    }

    // Up Arrow: History backward
    if (e.key === 'ArrowUp' && (!input.trim() || historyIndex !== -1)) {
      if (promptHistory.length > 0) {
        e.preventDefault();
        const nextIdx = Math.min(historyIndex + 1, promptHistory.length - 1);
        setHistoryIndex(nextIdx);
        setInput(promptHistory[nextIdx]);
      }
      return;
    }

    // Down Arrow: History forward
    if (e.key === 'ArrowDown' && historyIndex !== -1) {
      e.preventDefault();
      const prevIdx = historyIndex - 1;
      if (prevIdx < 0) {
        setHistoryIndex(-1);
        setInput('');
      } else {
        setHistoryIndex(prevIdx);
        setInput(promptHistory[prevIdx]);
      }
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
          content: 'Started new conversation. I can inspect live web pages, execute multi-agent browser tasks with LangGraph, conduct deep comparative research, and extract structured datasets.',
          timestamp: Date.now()
        }
      ],
      lastObservation: null,
      lastScreenshotUrl: null
    });
    setExportNotice('Conversation cleared');
    setTimeout(() => setExportNotice(null), 2000);
  };

  const handleExportChat = (format: 'markdown' | 'json') => {
    if (format === 'markdown') {
      const md = chatMessages.map(m => {
        const time = new Date(m.timestamp).toLocaleTimeString();
        const role = m.sender === 'user' ? '👤 User' : '🤖 Assistant';
        return `## ${role} (${time})\n\n${m.content}\n`;
      }).join('\n---\n\n');

      navigator.clipboard.writeText(md);
      setExportNotice('Copied chat as Markdown to clipboard!');
    } else {
      const json = JSON.stringify(chatMessages, null, 2);
      navigator.clipboard.writeText(json);
      setExportNotice('Copied chat as JSON to clipboard!');
    }
    setTimeout(() => setExportNotice(null), 2500);
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

  const handleTriggerSkill = (promptTemplate: string) => {
    setInput(promptTemplate);
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  // Safe stringification helpers to protect against unexpected object payloads
  const safeResultStr = typeof activeAction?.result === 'string'
    ? activeAction.result
    : (activeAction?.result ? JSON.stringify(activeAction.result) : '');

  const dialogReason = safeResultStr.includes('RED TIER')
    ? `🔴 RED TIER — ${safeResultStr}`
    : (safeResultStr || 'The autonomous agent is requesting permission to execute an action requiring user approval.');

  const safeThought = typeof activeAction?.thought === 'string'
    ? activeAction.thought
    : (activeAction?.thought ? JSON.stringify(activeAction.thought, null, 2) : '');

  const safePlan = typeof activeAction?.plan === 'string'
    ? activeAction.plan
    : (activeAction?.plan ? JSON.stringify(activeAction.plan, null, 2) : '');

  // Filter messages based on search query
  const displayedMessages = useMemo(() => {
    if (!searchQuery.trim()) return chatMessages;
    const q = searchQuery.toLowerCase();
    return chatMessages.filter(m => (m.content || '').toLowerCase().includes(q));
  }, [chatMessages, searchQuery]);

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <Sparkles size={16} style={{ color: 'var(--accent-primary)' }} />
          <span className={styles.headerTitle}>AI Assistant</span>
          {isAgentRunning ? (
            <span className={styles.modeBadge} style={{ background: '#f59e0b' }}>
              ACTION ACTIVE
            </span>
          ) : (
            <span className={styles.modeBadge} style={{ background: '#10b981' }}>
              RESEARCH
            </span>
          )}

          {isAgentRunning && elapsedSeconds > 0 && (
            <span className={styles.timerBadge}>
              <Clock size={10} />
              <span>{elapsedSeconds}s</span>
            </span>
          )}
        </div>

        <div className={styles.headerRight}>
          {isAgentRunning && (
            <button
              onClick={() => stopAssistant()}
              className={styles.stopBtn}
              title="Stop current agent action"
            >
              <Square size={10} fill="#fff" />
              <span>Stop</span>
            </button>
          )}

          {/* Engine Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
            <Layers size={12} style={{ color: 'var(--text-muted)' }} />
            <select
              value={selectedEngine}
              onChange={(e) => setSelectedEngine(e.target.value)}
              className={styles.badge}
              style={{ cursor: 'pointer', outline: 'none', maxWidth: '95px' }}
              title="Select Agent Runtime Engine"
            >
              {ENGINE_OPTIONS.map(opt => (
                <option key={opt.id} value={opt.id}>{opt.label}</option>
              ))}
            </select>
          </div>

          {/* Provider Selector Dropdown */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
            <Cpu size={12} style={{ color: 'var(--text-muted)' }} />
            <select
              value={selectedProvider}
              onChange={(e) => setSelectedProvider(e.target.value)}
              className={styles.badge}
              style={{ cursor: 'pointer', outline: 'none', maxWidth: '90px' }}
              title="Select Active AI Provider"
            >
              {PROVIDER_OPTIONS.map(p => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
          </div>

          {/* Search Toggle */}
          <button
            onClick={() => {
              setShowSearch(prev => !prev);
              if (showSearch) setSearchQuery('');
            }}
            className="icon-btn"
            style={{ width: '24px', height: '24px', color: showSearch ? 'var(--accent-primary)' : undefined }}
            title="Search In Conversation"
          >
            <Search size={13} />
          </button>

          {/* Export Chat */}
          <button
            onClick={() => handleExportChat('markdown')}
            className="icon-btn"
            style={{ width: '24px', height: '24px' }}
            title="Copy Chat as Markdown"
          >
            <Download size={13} />
          </button>

          {/* Clear Chat */}
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

      {/* Export Notice Banner */}
      {exportNotice && (
        <div style={{
          backgroundColor: 'var(--accent-subtle)',
          color: 'var(--accent-primary)',
          fontSize: '11px',
          padding: '4px 12px',
          textAlign: 'center',
          fontWeight: 600,
          borderBottom: '1px solid var(--border-subtle)'
        }}>
          {exportNotice}
        </div>
      )}

      {/* Search Input Bar (Collapsible) */}
      {showSearch && (
        <div className={styles.searchBar}>
          <Search size={13} style={{ color: 'var(--text-muted)' }} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conversation..."
            className={styles.searchInput}
            autoFocus
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="icon-btn"
              style={{ width: '18px', height: '18px' }}
            >
              <X size={11} />
            </button>
          )}
        </div>
      )}

      {/* Active Action Live Banner */}
      {isAgentRunning && activeAction && activeAction.status !== 'approval_required' && (
        <ProgressBanner
          action={typeof activeAction.action === 'string' ? activeAction.action : String(activeAction.action || '')}
          stepNumber={activeAction.step_number || '?'}
          totalSteps={activeAction.total_steps || '?'}
          url={typeof activeAction.parameters?.url === 'string' ? activeAction.parameters.url : undefined}
          query={typeof activeAction.parameters?.query === 'string' ? activeAction.parameters.query : undefined}
          question={typeof activeAction.parameters?.question === 'string' ? activeAction.parameters.question : undefined}
          parameters={activeAction.parameters}
        >
          <div className={`${styles.activeActionBanner} animate-slide-in-down`}>
            <div className={styles.pulseDot} />
            <span style={{ fontWeight: 500 }}>
              {activeAction.action === 'synthesizing' ? (
                <>🧠 <strong>Synthesizing final response...</strong></>
              ) : activeAction.status === 'completed' ? (
                <>✓ Completed: <strong>{String(activeAction.action || '')}</strong> — Synthesizing answer...</>
              ) : (
                <>
                  {activeAction.step_number && activeAction.step_number !== '?'
                    ? `Running Step ${activeAction.step_number}/${activeAction.total_steps || '?'}: `
                    : 'Executing: '}
                  <strong>{String(activeAction.action || '')}</strong>
                  {activeAction.parameters?.url ? ` (${typeof activeAction.parameters.url === 'string' ? activeAction.parameters.url : JSON.stringify(activeAction.parameters.url)})` : ''}
                  {activeAction.parameters?.query ? ` "${typeof activeAction.parameters.query === 'string' ? activeAction.parameters.query : JSON.stringify(activeAction.parameters.query)}"` : ''}
                  {activeAction.parameters?.question ? ` (${typeof activeAction.parameters.question === 'string' ? activeAction.parameters.question : JSON.stringify(activeAction.parameters.question)})` : ''}
                </>
              )}
            </span>
          </div>
        </ProgressBanner>
      )}

      {/* ReAct Thought/Plan Trace */}
      {isAgentRunning && safeThought && (
        <div className={styles.reactTrace}>
          <div className={styles.reactTraceHeader} onClick={() => setShowTrace(t => !t)}>
            <span>🧠 Agent Reasoning Trace</span>
            <span>{showTrace ? '▲' : '▼'}</span>
          </div>
          {showTrace && (
            <div className={styles.reactTraceBody}>
              <pre className={styles.reactThought}>{safeThought}</pre>
              {safePlan && (
                <div className={styles.reactPlan}>
                  <strong>Plan:</strong>
                  <pre>{safePlan}</pre>
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
        reason={dialogReason}
        toolName={typeof activeAction?.action === 'string' ? activeAction.action : String(activeAction?.action || '')}
        parameters={activeAction?.parameters}
        onApprove={() => {
          const taskId = (activeAction as any)?.task_id || activeAction?.parameters?.task_id;
          const executionId = (activeAction as any)?.execution_id || activeAction?.parameters?.execution_id;
          const approvalId = (activeAction as any)?.approval_id || activeAction?.parameters?.approval_id;
          if (taskId && window.electronAPI?.approveTask) {
            window.electronAPI.approveTask(taskId, true, approvalId);
          } else if (executionId && (window.electronAPI as any)?.resumeWorkflow) {
            (window.electronAPI as any).resumeWorkflow(executionId, true, approvalId);
          }
          setActiveAction(null);
        }}
        onReject={() => {
          const taskId = (activeAction as any)?.task_id || activeAction?.parameters?.task_id;
          const executionId = (activeAction as any)?.execution_id || activeAction?.parameters?.execution_id;
          const approvalId = (activeAction as any)?.approval_id || activeAction?.parameters?.approval_id;
          if (taskId && window.electronAPI?.rejectTask) {
            window.electronAPI.rejectTask(taskId, undefined, approvalId);
          } else if (executionId && (window.electronAPI as any)?.resumeWorkflow) {
            (window.electronAPI as any).resumeWorkflow(executionId, false, approvalId);
          }
          setActiveAction(null);
          stopAssistant();
        }}
      />

      {/* Action Matrix Categories */}
      <div className={styles.categoryNav}>
        <button
          onClick={() => setActiveCategory('research')}
          className={`${styles.categoryTab} ${activeCategory === 'research' ? styles.categoryTabActive : ''}`}
        >
          🔍 Research
        </button>
        <button
          onClick={() => setActiveCategory('automation')}
          className={`${styles.categoryTab} ${activeCategory === 'automation' ? styles.categoryTabActive : ''}`}
        >
          ⚡ Automation
        </button>
        <button
          onClick={() => setActiveCategory('inspect')}
          className={`${styles.categoryTab} ${activeCategory === 'inspect' ? styles.categoryTabActive : ''}`}
        >
          🛠️ Inspect & CDP
        </button>
      </div>

      {/* Quick Action Chips filtered by Category */}
      <div className={styles.quickChips}>
        {activeCategory === 'research' && (
          <>
            <button onClick={handleDeepResearch} className={styles.chipBtn} title="Deep Multi-Hop Research">
              <Sparkles size={12} style={{ color: 'var(--accent-primary)' }} />
              <span>Deep Research</span>
            </button>

            <button onClick={handleCompareTabs} className={styles.chipBtn} title="Cross-compare all open browser tabs">
              <Globe size={12} style={{ color: '#8b5cf6' }} />
              <span>Cross-Compare Tabs</span>
            </button>

            <button onClick={handleQuickSummarize} className={styles.chipBtn} title="Synthesize current page">
              <FileText size={12} />
              <span>Summarize Page</span>
            </button>

            <button onClick={handleQuickCompare} className={styles.chipBtn} title="Compare product options and specs">
              <TrendingUp size={12} style={{ color: '#10b981' }} />
              <span>Compare Specs & Prices</span>
            </button>
          </>
        )}

        {activeCategory === 'automation' && (
          <>
            <button onClick={handleQuickTableExtraction} className={styles.chipBtn} title="Extract tabular datasets to CSV">
              <Table size={12} style={{ color: '#f59e0b' }} />
              <span>Extract Table to CSV</span>
            </button>

            <button onClick={() => handleTriggerSkill('/skill:form_automation Autofill and inspect all inputs on this page')} className={styles.chipBtn} title="Form Auto-fill">
              <FileText size={12} style={{ color: '#ec4899' }} />
              <span>Form Automation</span>
            </button>

            <button onClick={() => handleTriggerSkill('/skill:web_scraper Extract structured data from this page')} className={styles.chipBtn} title="Web Scraper">
              <Table size={12} style={{ color: '#06b6d4' }} />
              <span>Web Scraper</span>
            </button>

            <button onClick={() => handleTriggerSkill('Collect and verify all outbound links on this page')} className={styles.chipBtn} title="Link Collector">
              <Globe size={12} style={{ color: '#3b82f6' }} />
              <span>Crawl Outbound Links</span>
            </button>
          </>
        )}

        {activeCategory === 'inspect' && (
          <>
            <button onClick={handleQuickInspect} className={styles.chipBtn} title="Inspect live DOM and accessibility tree">
              <ShieldCheck size={12} style={{ color: 'var(--accent-primary)' }} />
              <span>Inspect CDP Elements</span>
            </button>

            <button onClick={() => capturePage()} className={styles.chipBtn} title="Capture viewport snapshot">
              <Camera size={12} />
              <span>Capture Screenshot</span>
            </button>

            <button onClick={() => handleTriggerSkill('/skill:dev_seo_auditor Perform complete SEO and accessibility audit')} className={styles.chipBtn} title="SEO Audit">
              <Cpu size={12} style={{ color: '#3b82f6' }} />
              <span>SEO & DOM Audit</span>
            </button>

            <button onClick={() => handleTriggerSkill('/skill:session_inspector Inspect cookies and storage tokens')} className={styles.chipBtn} title="Cookies Inspector">
              <ShieldCheck size={12} style={{ color: '#10b981' }} />
              <span>Session & Cookies</span>
            </button>
          </>
        )}
      </div>

      {/* Messages Scroll Area */}
      <div ref={scrollRef} className={styles.chatList}>
        {displayedMessages.map(msg => (
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
              <span style={{ fontWeight: 600 }}>Active Tab Perception Attached</span>
            </div>
            <div style={{ color: 'var(--text-secondary)' }}>
              <div><strong>URL:</strong> {lastObservation.url}</div>
              <div><strong>Viewport:</strong> {lastObservation.viewport.width} x {lastObservation.viewport.height}</div>
              <div><strong>Elements:</strong> {lastObservation.interactiveElements.length} interactive elements detected</div>
              <div><strong>Visible text:</strong> {lastObservation.visibleText.slice(0, 120)}...</div>
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

      {/* Live Page Context Pill Bar */}
      <div className={styles.contextBar}>
        <div className={styles.contextTabInfo} title={activeTab?.url || 'No active webpage'}>
          <Globe size={11} style={{ flexShrink: 0, color: 'var(--accent-primary)' }} />
          <span>{activeTab?.title || activeTab?.url || 'Blank Tab'}</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
          <button
            type="button"
            onClick={() => setIncludeContext(!includeContext)}
            className={`${styles.contextPill} ${includeContext ? styles.contextPillActive : ''}`}
            title="Toggle live page DOM and visible text inclusion in query"
          >
            {includeContext ? <Check size={10} /> : null}
            <span>Page Context</span>
          </button>

          <button
            type="button"
            onClick={() => setAttachScreenshot(!attachScreenshot)}
            className={`${styles.contextPill} ${attachScreenshot ? styles.contextPillActive : ''}`}
            title="Attach live viewport screenshot to query"
          >
            <Camera size={10} />
            <span>+Screenshot</span>
          </button>
        </div>
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
            placeholder="Ask AI, delegate LangGraph multi-agent task, or search web (↑ for history)..."
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
            title="Send prompt or execute task (Enter)"
          >
            <Send size={14} />
          </button>
        </div>
      </div>
    </div>
  );
};
