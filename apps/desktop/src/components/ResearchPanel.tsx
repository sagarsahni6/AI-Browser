import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  FileText,
  Search,
  BookOpen,
  Trash2,
  Download,
  ChevronDown,
  ChevronRight,
  ExternalLink
} from 'lucide-react';
import styles from './ResearchPanel.module.css';

interface ResearchReportItem {
  id: string;
  topic: string;
  summary?: string;
  created_at: number;
  sources_count: number;
}

export const ResearchPanel: React.FC = () => {
  const [reports, setReports] = useState<ResearchReportItem[]>([]);
  const [topic, setTopic] = useState('');
  const [depth, setDepth] = useState<'quick' | 'deep'>('quick');
  const [pdfPath, setPdfPath] = useState('');
  const [loadingResearch, setLoadingResearch] = useState(false);
  const [loadingPdf, setLoadingPdf] = useState(false);
  const [activeReportDetail, setActiveReportDetail] = useState<{ id: string; content_markdown: string } | null>(null);
  const [pdfSummaryResult, setPdfSummaryResult] = useState<string | null>(null);

  const loadReports = async () => {
    if (window.electronAPI?.listResearchReports) {
      try {
        const list = await window.electronAPI.listResearchReports();
        setReports(list || []);
      } catch (err) {
        console.error('Failed to list research reports:', err);
      }
    }
  };

  useEffect(() => {
    loadReports();
  }, []);

  const handleSynthesize = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim() || loadingResearch || !window.electronAPI?.synthesizeResearch) return;

    setLoadingResearch(true);
    try {
      const res = await window.electronAPI.synthesizeResearch({
        topic: topic.trim(),
        depth
      });
      if (res && res.report_id) {
        setTopic('');
        loadReports();
        if (res.content_markdown) {
          setActiveReportDetail({ id: res.report_id, content_markdown: res.content_markdown });
        }
      }
    } catch (err) {
      console.error('Research synthesis failed:', err);
    } finally {
      setLoadingResearch(false);
    }
  };

  const handlePdfSummarize = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pdfPath.trim() || loadingPdf || !window.electronAPI?.summarizePdf) return;

    setLoadingPdf(true);
    setPdfSummaryResult(null);
    try {
      const res = await window.electronAPI.summarizePdf({ path_or_url: pdfPath.trim() });
      if (res.status === 'ok') {
        setPdfSummaryResult(res.summary);
      } else {
        setPdfSummaryResult(`Error: ${res.error || 'Failed to read PDF'}`);
      }
    } catch (err) {
      setPdfSummaryResult(`Exception: ${(err as Error).message}`);
    } finally {
      setLoadingPdf(false);
    }
  };

  const handleToggleReport = async (reportId: string) => {
    if (activeReportDetail?.id === reportId) {
      setActiveReportDetail(null);
      return;
    }
    if (window.electronAPI?.getResearchReport) {
      try {
        const full = await window.electronAPI.getResearchReport(reportId);
        if (full) {
          setActiveReportDetail({ id: full.id, content_markdown: full.content_markdown });
        }
      } catch (err) {
        console.error('Failed to load report:', err);
      }
    }
  };

  const handleDeleteReport = async (reportId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.electronAPI?.deleteResearchReport) {
      await window.electronAPI.deleteResearchReport(reportId);
      if (activeReportDetail?.id === reportId) setActiveReportDetail(null);
      loadReports();
    }
  };

  const handleExportMarkdown = (content: string, filename: string) => {
    const dataStr = 'data:text/markdown;charset=utf-8,' + encodeURIComponent(content);
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `${filename.replace(/[^a-zA-Z0-9_-]/g, '_')}.md`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.titleGroup}>
          <BookOpen size={14} style={{ color: 'var(--accent-primary)' }} />
          <span style={{ fontSize: '11px', fontWeight: 600, textTransform: 'uppercase' }}>
            Research & Intelligence
          </span>
        </div>
      </div>

      {/* Deep Research Section */}
      <form onSubmit={handleSynthesize} className={styles.card}>
        <div className={styles.cardTitle}>
          <Sparkles size={13} style={{ color: 'var(--accent-primary)' }} />
          <span>Deep Research Engine</span>
        </div>
        <input
          type="text"
          placeholder="Research topic (e.g. LLM agent architectures)"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          className={styles.input}
          required
        />
        <div className={styles.btnRow}>
          <select
            value={depth}
            onChange={(e) => setDepth(e.target.value as 'quick' | 'deep')}
            style={{
              fontSize: '11px',
              padding: '4px 6px',
              background: 'var(--bg-secondary)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)'
            }}
          >
            <option value="quick">Quick (5 sources)</option>
            <option value="deep">Deep (Multi-angle)</option>
          </select>
          <button type="submit" disabled={loadingResearch || !topic.trim()} className={styles.primaryBtn}>
            <Search size={12} />
            <span>{loadingResearch ? 'Synthesizing...' : 'Start Research'}</span>
          </button>
        </div>
      </form>

      {/* PDF Intelligence Section */}
      <form onSubmit={handlePdfSummarize} className={styles.card}>
        <div className={styles.cardTitle}>
          <FileText size={13} style={{ color: 'var(--accent-primary)' }} />
          <span>PDF & Document Analysis</span>
        </div>
        <input
          type="text"
          placeholder="Local PDF path or URL (e.g. C:/docs/paper.pdf)"
          value={pdfPath}
          onChange={(e) => setPdfPath(e.target.value)}
          className={styles.input}
          required
        />
        <div className={styles.btnRow}>
          <span style={{ fontSize: '10.5px', color: 'var(--text-muted)' }}>Page-level citations</span>
          <button type="submit" disabled={loadingPdf || !pdfPath.trim()} className={styles.primaryBtn}>
            <FileText size={12} />
            <span>{loadingPdf ? 'Parsing...' : 'Summarize PDF'}</span>
          </button>
        </div>

        {pdfSummaryResult && (
          <div className={styles.reportPreview} style={{ marginTop: '6px' }}>
            {pdfSummaryResult}
          </div>
        )}
      </form>

      {/* Reports List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
          Saved Research Reports ({reports.length})
        </div>

        {reports.length === 0 ? (
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center', padding: '12px 0' }}>
            No research reports yet. Enter a topic above to generate a cited synthesis.
          </div>
        ) : (
          reports.map((rep) => {
            const isExpanded = activeReportDetail?.id === rep.id;

            return (
              <div key={rep.id} className={styles.reportItem}>
                <div
                  onClick={() => handleToggleReport(rep.id)}
                  style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {isExpanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                    <div>
                      <div className={styles.reportTopic}>{rep.topic}</div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                        {rep.sources_count} sources &bull; {new Date(rep.created_at * 1000).toLocaleDateString()}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '4px' }}>
                    <button
                      onClick={(e) => handleDeleteReport(rep.id, e)}
                      title="Delete"
                      className={styles.iconBtn}
                      style={{ color: 'var(--error)' }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>

                {isExpanded && activeReportDetail && (
                  <div style={{ marginTop: '6px' }}>
                    <div className={styles.reportPreview}>
                      {activeReportDetail.content_markdown}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
                      <button
                        onClick={() => handleExportMarkdown(activeReportDetail.content_markdown, rep.topic)}
                        className={styles.subBtn}
                        style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
                      >
                        <Download size={11} /> Export Markdown
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
