import React, { useState } from 'react';
import { User, Bot, Copy, Check, ChevronDown, ChevronRight, Terminal } from 'lucide-react';
import { MarkdownRenderer } from './MarkdownRenderer';
import styles from './ChatMessage.module.css';

export interface ChatMessageProps {
  id: string;
  sender: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  metadata?: {
    model?: string;
    toolCalls?: Array<{ name: string; parameters?: any; result?: any }>;
    citations?: Array<{ title: string; url: string }>;
  };
}

export const ChatMessageItem: React.FC<ChatMessageProps> = ({
  sender,
  content,
  metadata
}) => {
  const [copied, setCopied] = useState(false);
  const [showTools, setShowTools] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isUser = sender === 'user';

  // Extract and clean any embedded tool call XML tags so users never see raw markup
  const hasEmbeddedToolCall = !isUser && typeof content === 'string' && content.includes('<tool_call>');
  let displayContent = typeof content === 'string' ? content : String(content || '');
  let inlineToolName = '';

  if (hasEmbeddedToolCall) {
    const fnMatch = content.match(/<function(?:=|\s+name=)[\"']?([a-zA-Z0-9_\-]+)[\"']?>/i);
    if (fnMatch) {
      inlineToolName = fnMatch[1];
    }
    displayContent = content.replace(/<tool_call>[\s\S]*?<\/tool_call>/gi, '').trim();
    if (!displayContent) {
      displayContent = inlineToolName
        ? `*Executed browser action: \`${inlineToolName}\`*`
        : '*Processing browser automation...*';
    }
  }

  return (
    <div className={`${styles.row} ${isUser ? styles.rowUser : ''}`}>
      <div className={`${styles.avatar} ${isUser ? styles.avatarUser : styles.avatarBot}`}>
        {isUser ? <User size={12} /> : <Bot size={12} />}
      </div>

      <div className={`${styles.bubble} ${isUser ? styles.bubbleUser : styles.bubbleBot}`}>
        {/* Model header tag if provided */}
        {!isUser && metadata?.model && (
          <div className={styles.modelTag}>
            {metadata.model}
          </div>
        )}

        {/* Inline tool executed indicator if extracted from message */}
        {inlineToolName && (
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '11px', color: 'var(--accent-primary)', marginBottom: '6px', fontWeight: 600 }}>
            <Terminal size={12} />
            <span>Automated Action: {inlineToolName}</span>
          </div>
        )}

        {/* Tool Execution Logs (Collapsible) */}
        {!isUser && metadata?.toolCalls && metadata.toolCalls.length > 0 && (
          <div className={styles.toolsAccordion}>
            <button
              onClick={() => setShowTools(!showTools)}
              className={styles.toolsHeader}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <Terminal size={12} style={{ color: 'var(--accent-primary)' }} />
                <span>{metadata.toolCalls.length} tool {metadata.toolCalls.length === 1 ? 'call' : 'calls'} executed</span>
              </div>
              {showTools ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            </button>
            {showTools && (
              <div className={styles.toolsBody}>
                {metadata.toolCalls.map((t, idx) => (
                  <div key={idx} className={styles.toolItem}>
                    <span className={styles.toolName}>▶ {t.name}</span>
                    {t.parameters && (
                      <pre className={styles.toolJson}>
                        {JSON.stringify(t.parameters, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Message Content */}
        {isUser ? (
          <div style={{ whiteSpace: 'pre-wrap' }}>{displayContent}</div>
        ) : (
          <MarkdownRenderer content={displayContent} />
        )}

        {/* Copy button on hover for assistant messages */}
        {!isUser && content && (
          <div className={styles.actionRow}>
            <button
              onClick={handleCopy}
              className={styles.actionBtn}
              title="Copy response"
            >
              {copied ? <Check size={11} /> : <Copy size={11} />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
