import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import styles from './MarkdownRenderer.module.css';

interface MarkdownRendererProps {
  content: string;
  onCitationClick?: (index: number) => void;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, onCitationClick }) => {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const handleCopyCode = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const renderInline = (text: string): React.ReactNode[] => {
    // Regex for inline code, citations [1], bold **text**, and links [text](url)
    const tokenRegex = /(`[^`]+`)|(\[\d+\])|(\*\*[^*]+\*\*)|(\[[^\]]+\]\([^)]+\))/g;
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = tokenRegex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(text.slice(lastIndex, match.index));
      }

      const matchText = match[0];
      if (matchText.startsWith('`') && matchText.endsWith('`')) {
        parts.push(
          <code key={match.index} className={styles.inlineCode}>
            {matchText.slice(1, -1)}
          </code>
        );
      } else if (matchText.startsWith('[') && matchText.endsWith(']') && /^\d+$/.test(matchText.slice(1, -1))) {
        const num = parseInt(matchText.slice(1, -1), 10);
        parts.push(
          <span
            key={match.index}
            className={styles.citationLink}
            onClick={() => onCitationClick?.(num)}
            title={`Citation [${num}]`}
          >
            {num}
          </span>
        );
      } else if (matchText.startsWith('**') && matchText.endsWith('**')) {
        parts.push(
          <strong key={match.index}>
            {matchText.slice(2, -2)}
          </strong>
        );
      } else if (matchText.startsWith('[') && matchText.includes('](')) {
        const linkMatch = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(matchText);
        if (linkMatch) {
          parts.push(
            <a
              key={match.index}
              href={linkMatch[2]}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: 'var(--accent-primary)', textDecoration: 'underline' }}
            >
              {linkMatch[1]}
            </a>
          );
        } else {
          parts.push(matchText);
        }
      }

      lastIndex = tokenRegex.lastIndex;
    }

    if (lastIndex < text.length) {
      parts.push(text.slice(lastIndex));
    }

    return parts;
  };

  const renderBlocks = () => {
    const lines = content.split('\n');
    const elements: React.ReactNode[] = [];
    let i = 0;
    let blockIndex = 0;

    while (i < lines.length) {
      const line = lines[i];

      // Code Block
      if (line.startsWith('```')) {
        const lang = line.slice(3).trim() || 'code';
        const codeLines: string[] = [];
        i++;
        while (i < lines.length && !lines[i].startsWith('```')) {
          codeLines.push(lines[i]);
          i++;
        }
        i++; // skip closing ```
        const codeText = codeLines.join('\n');
        const curIndex = blockIndex++;
        elements.push(
          <div key={`code-${curIndex}`} className={styles.codeBlock}>
            <div className={styles.codeHeader}>
              <span>{lang}</span>
              <button
                className={styles.copyBtn}
                onClick={() => handleCopyCode(codeText, curIndex)}
                title="Copy code"
              >
                {copiedIndex === curIndex ? <Check size={12} /> : <Copy size={12} />}
                <span>{copiedIndex === curIndex ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <pre className={styles.codePre}>
              <code>{codeText}</code>
            </pre>
          </div>
        );
        continue;
      }

      // Headings
      if (line.startsWith('### ')) {
        elements.push(<h3 key={`h3-${i}`}>{renderInline(line.slice(4))}</h3>);
        i++;
        continue;
      }
      if (line.startsWith('## ')) {
        elements.push(<h2 key={`h2-${i}`}>{renderInline(line.slice(3))}</h2>);
        i++;
        continue;
      }
      if (line.startsWith('# ')) {
        elements.push(<h1 key={`h1-${i}`}>{renderInline(line.slice(2))}</h1>);
        i++;
        continue;
      }

      // Blockquote
      if (line.startsWith('> ')) {
        elements.push(<blockquote key={`quote-${i}`}>{renderInline(line.slice(2))}</blockquote>);
        i++;
        continue;
      }

      // Unordered List
      if (line.startsWith('- ') || line.startsWith('* ')) {
        const listItems: React.ReactNode[] = [];
        while (i < lines.length && (lines[i].startsWith('- ') || lines[i].startsWith('* '))) {
          listItems.push(<li key={`li-${i}`}>{renderInline(lines[i].slice(2))}</li>);
          i++;
        }
        elements.push(<ul key={`ul-${i}`}>{listItems}</ul>);
        continue;
      }

      // Ordered List
      if (/^\d+\.\s/.test(line)) {
        const listItems: React.ReactNode[] = [];
        while (i < lines.length && /^\d+\.\s/.test(lines[i])) {
          const textAfterNum = lines[i].replace(/^\d+\.\s/, '');
          listItems.push(<li key={`oli-${i}`}>{renderInline(textAfterNum)}</li>);
          i++;
        }
        elements.push(<ol key={`ol-${i}`}>{listItems}</ol>);
        continue;
      }

      // Table detection
      if (line.startsWith('|') && line.endsWith('|')) {
        const tableRows: string[] = [];
        while (i < lines.length && lines[i].startsWith('|') && lines[i].endsWith('|')) {
          tableRows.push(lines[i]);
          i++;
        }
        if (tableRows.length >= 2) {
          const headerCells = tableRows[0].split('|').slice(1, -1).map(c => c.trim());
          const bodyRows = tableRows.slice(2); // skip separator line
          elements.push(
            <div key={`table-${i}`} className={styles.tableWrapper}>
              <table>
                <thead>
                  <tr>
                    {headerCells.map((h, hIdx) => (
                      <th key={hIdx}>{renderInline(h)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {bodyRows.map((r, rIdx) => {
                    const cells = r.split('|').slice(1, -1).map(c => c.trim());
                    return (
                      <tr key={rIdx}>
                        {cells.map((c, cIdx) => (
                          <td key={cIdx}>{renderInline(c)}</td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          );
          continue;
        }
      }

      // Empty line
      if (!line.trim()) {
        i++;
        continue;
      }

      // Standard paragraph
      elements.push(<p key={`p-${i}`}>{renderInline(line)}</p>);
      i++;
    }

    return elements;
  };

  return <div className={styles.markdown}>{renderBlocks()}</div>;
};
