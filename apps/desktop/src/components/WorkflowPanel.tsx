import React, { useState, useEffect } from 'react';
import {
  Play,
  Square,
  Circle,
  Plus,
  Trash2,
  Download,
  Upload,
  ChevronDown,
  ChevronRight,
  Workflow as WorkflowIcon,
  CheckCircle,
  AlertCircle,
  Clock
} from 'lucide-react';
import styles from './WorkflowPanel.module.css';

interface WorkflowStep {
  name?: string;
  action: string;
  params: Record<string, any>;
  description?: string;
}

interface Workflow {
  id: string;
  name: string;
  description?: string;
  steps: WorkflowStep[];
  parameters?: Record<string, any>;
  created_at: number;
}

export const WorkflowPanel: React.FC = () => {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [importJson, setImportJson] = useState('');
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [recordedSteps, setRecordedSteps] = useState<any[]>([]);
  const [executingWorkflowId, setExecutingWorkflowId] = useState<string | null>(null);
  const [activeStepProgress, setActiveStepProgress] = useState<{ step: number; total: number; status: string; action: string } | null>(null);
  const [executionLog, setExecutionLog] = useState<string[]>([]);

  // Parameter modal for workflows with variables
  const [paramModalWorkflow, setParamModalWorkflow] = useState<Workflow | null>(null);
  const [paramValues, setParamValues] = useState<Record<string, string>>({});

  const loadWorkflows = async () => {
    if (window.electronAPI?.listWorkflows) {
      try {
        const list = await window.electronAPI.listWorkflows();
        setWorkflows(list || []);
      } catch (err) {
        console.error('Failed to list workflows:', err);
      }
    }
  };

  useEffect(() => {
    loadWorkflows();

    if (window.electronAPI?.onWorkflowStepUpdate) {
      const cleanup = window.electronAPI.onWorkflowStepUpdate((data: any) => {
        if (data.status === 'completed' || data.status === 'failed') {
          setActiveStepProgress(null);
          setExecutingWorkflowId(null);
          setExecutionLog((prev) => [...prev, `[${data.status.toUpperCase()}] Workflow finished`]);
        } else {
          setActiveStepProgress({
            step: data.stepIndex + 1,
            total: data.totalSteps,
            status: data.status,
            action: data.action
          });
          setExecutionLog((prev) => [
            ...prev,
            `Step ${data.stepIndex + 1}/${data.totalSteps}: ${data.action} -> ${data.status}`
          ]);
        }
      });
      return cleanup;
    }
  }, []);

  const handleToggleRecord = async () => {
    if (!isRecording) {
      if (window.electronAPI?.startWorkflowRecording) {
        try {
          await window.electronAPI.startWorkflowRecording();
          setIsRecording(true);
        } catch (err) {
          console.error('Failed to start recording:', err);
        }
      }
    } else {
      if (window.electronAPI?.stopWorkflowRecording) {
        try {
          const steps = await window.electronAPI.stopWorkflowRecording();
          setIsRecording(false);
          setRecordedSteps(steps || []);
          setShowCreateModal(true);
        } catch (err) {
          console.error('Failed to stop recording:', err);
          setIsRecording(false);
        }
      }
    }
  };

  const handleSaveRecorded = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim() || !window.electronAPI?.saveWorkflow) return;

    try {
      await window.electronAPI.saveWorkflow({
        name: newName.trim(),
        description: newDesc.trim(),
        steps: recordedSteps.length > 0 ? recordedSteps : [{ action: 'navigate', params: { url: 'https://example.com' } }]
      });
      setNewName('');
      setNewDesc('');
      setRecordedSteps([]);
      setShowCreateModal(false);
      loadWorkflows();
    } catch (err) {
      console.error('Failed to save workflow:', err);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.electronAPI?.deleteWorkflow) {
      await window.electronAPI.deleteWorkflow(id);
      loadWorkflows();
    }
  };

  const handleExport = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.electronAPI?.exportWorkflow) {
      try {
        const exported = await window.electronAPI.exportWorkflow(id);
        const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(exported, null, 2));
        const downloadAnchor = document.createElement('a');
        downloadAnchor.setAttribute('href', dataStr);
        downloadAnchor.setAttribute('download', `workflow-${id.slice(0, 8)}.json`);
        document.body.appendChild(downloadAnchor);
        downloadAnchor.click();
        downloadAnchor.remove();
      } catch (err) {
        console.error('Failed to export workflow:', err);
      }
    }
  };

  const handleImportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!importJson.trim() || !window.electronAPI?.importWorkflow) return;

    try {
      const parsed = JSON.parse(importJson);
      await window.electronAPI.importWorkflow(parsed);
      setImportJson('');
      setShowImportModal(false);
      loadWorkflows();
    } catch (err) {
      alert('Invalid Workflow JSON: ' + (err as Error).message);
    }
  };

  const findVariables = (wf: Workflow): string[] => {
    const raw = JSON.stringify(wf.steps);
    const matches = raw.match(/\{\{([a-zA-Z0-9_-]+)\}\}/g);
    if (!matches) return [];
    return Array.from(new Set(matches.map((m) => m.replace(/[{}]/g, ''))));
  };

  const handleExecuteClick = (wf: Workflow) => {
    const vars = findVariables(wf);
    if (vars.length > 0) {
      const initVals: Record<string, string> = {};
      vars.forEach((v) => { initVals[v] = ''; });
      setParamValues(initVals);
      setParamModalWorkflow(wf);
    } else {
      executeWorkflowDirect(wf.id, {});
    }
  };

  const executeWorkflowDirect = async (id: string, variables: Record<string, any>) => {
    if (!window.electronAPI?.executeWorkflow) return;
    setExecutingWorkflowId(id);
    setExecutionLog([`Starting execution of workflow ${id}...`]);
    try {
      await window.electronAPI.executeWorkflow(id, variables);
    } catch (err) {
      console.error('Execution failed:', err);
      setExecutionLog((prev) => [...prev, `Execution error: ${(err as Error).message}`]);
      setExecutingWorkflowId(null);
    }
  };

  return (
    <div className={styles.container}>
      {/* Top Controls Header */}
      <div className={styles.header}>
        <div className={styles.titleGroup}>
          <WorkflowIcon size={14} style={{ color: 'var(--accent-primary)' }} />
          <span style={{ fontSize: '11px', fontWeight: 600, textTransform: 'uppercase' }}>
            Workflows ({workflows.length})
          </span>
        </div>

        <button
          onClick={handleToggleRecord}
          className={`${styles.recordBtn} ${isRecording ? styles.recordingActive : ''}`}
        >
          <span className={`${styles.dot} ${isRecording ? styles.dotPulse : ''}`} />
          <span>{isRecording ? 'Stop Recording' : 'Record'}</span>
        </button>
      </div>

      {/* Sub navigation actions */}
      <div className={styles.actionRow}>
        <button onClick={() => setShowCreateModal(true)} className={styles.subBtn}>
          + New Workflow
        </button>
        <button onClick={() => setShowImportModal(true)} className={styles.subBtn}>
          Import JSON
        </button>
      </div>

      {/* Active step progress banner */}
      {activeStepProgress && (
        <div className={styles.statusBanner}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
            <span style={{ fontWeight: 600, color: 'var(--accent-primary)' }}>
              Executing: {activeStepProgress.action}
            </span>
            <span>
              {activeStepProgress.step} / {activeStepProgress.total}
            </span>
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
            Status: {activeStepProgress.status}
          </div>
        </div>
      )}

      {/* Modal / Form for Creating / Saving Recorded Workflow */}
      {showCreateModal && (
        <form onSubmit={handleSaveRecorded} className={styles.formCard}>
          <div style={{ fontSize: '11.5px', fontWeight: 600 }}>
            {recordedSteps.length > 0 ? `Save Recorded Workflow (${recordedSteps.length} steps)` : 'Create New Workflow'}
          </div>
          <input
            type="text"
            placeholder="Workflow Name (e.g. Scrape Price to Sheet)"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className={styles.input}
            required
            autoFocus
          />
          <input
            type="text"
            placeholder="Description (optional)"
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
            className={styles.input}
          />
          <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end', marginTop: '4px' }}>
            <button
              type="button"
              onClick={() => { setShowCreateModal(false); setRecordedSteps([]); }}
              className={styles.subBtn}
            >
              Cancel
            </button>
            <button type="submit" disabled={!newName.trim()} className={styles.primaryBtn}>
              Save Workflow
            </button>
          </div>
        </form>
      )}

      {/* Modal for Importing Workflow JSON */}
      {showImportModal && (
        <form onSubmit={handleImportSubmit} className={styles.formCard}>
          <div style={{ fontSize: '11.5px', fontWeight: 600 }}>Import Workflow JSON</div>
          <textarea
            placeholder="Paste workflow JSON structure here..."
            value={importJson}
            onChange={(e) => setImportJson(e.target.value)}
            className={styles.input}
            rows={5}
            required
          />
          <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end', marginTop: '4px' }}>
            <button type="button" onClick={() => setShowImportModal(false)} className={styles.subBtn}>
              Cancel
            </button>
            <button type="submit" disabled={!importJson.trim()} className={styles.primaryBtn}>
              Import
            </button>
          </div>
        </form>
      )}

      {/* Parameter modal before execution */}
      {paramModalWorkflow && (
        <div className={styles.formCard}>
          <div style={{ fontSize: '11.5px', fontWeight: 600 }}>Set Parameters for {paramModalWorkflow.name}</div>
          {Object.keys(paramValues).map((key) => (
            <div key={key}>
              <div style={{ fontSize: '10.5px', color: 'var(--text-secondary)', marginBottom: '2px' }}>{key}:</div>
              <input
                type="text"
                placeholder={`Value for {{${key}}}`}
                value={paramValues[key]}
                onChange={(e) => setParamValues({ ...paramValues, [key]: e.target.value })}
                className={styles.input}
              />
            </div>
          ))}
          <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end', marginTop: '6px' }}>
            <button type="button" onClick={() => setParamModalWorkflow(null)} className={styles.subBtn}>
              Cancel
            </button>
            <button
              type="button"
              onClick={() => {
                const wf = paramModalWorkflow;
                setParamModalWorkflow(null);
                executeWorkflowDirect(wf.id, paramValues);
              }}
              className={styles.primaryBtn}
            >
              Run Workflow
            </button>
          </div>
        </div>
      )}

      {/* Workflows List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {workflows.length === 0 ? (
          <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', textAlign: 'center', padding: '16px 0' }}>
            No saved workflows. Click "Record" to record active tab interactions or "+ New Workflow".
          </div>
        ) : (
          workflows.map((wf) => {
            const isExpanded = expandedId === wf.id;
            const isRunning = executingWorkflowId === wf.id;
            const stepsCount = Array.isArray(wf.steps) ? wf.steps.length : 0;

            return (
              <div key={wf.id} className={styles.workflowCard}>
                <div className={styles.cardTop}>
                  <div
                    onClick={() => setExpandedId(isExpanded ? null : wf.id)}
                    style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', flex: 1 }}
                  >
                    {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    <div>
                      <div className={styles.cardTitle}>{wf.name}</div>
                      {wf.description && <div className={styles.cardDesc}>{wf.description}</div>}
                    </div>
                  </div>
                  <span className={styles.stepBadge}>{stepsCount} steps</span>
                </div>

                {/* Steps Accordion */}
                {isExpanded && (
                  <div className={styles.stepsList}>
                    {stepsCount === 0 ? (
                      <div>No steps defined</div>
                    ) : (
                      wf.steps.map((st, idx) => (
                        <div key={idx} className={styles.stepRow}>
                          <span style={{ color: 'var(--text-muted)' }}>{idx + 1}.</span>
                          <span style={{ fontWeight: 600 }}>{st.action}</span>
                          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {JSON.stringify(st.params)}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {/* Card Controls */}
                <div className={styles.cardControls}>
                  <button
                    onClick={() => handleExecuteClick(wf)}
                    disabled={isRunning}
                    className={styles.playBtn}
                  >
                    <Play size={11} />
                    <span>{isRunning ? 'Running...' : 'Run'}</span>
                  </button>

                  <div style={{ display: 'flex', gap: '4px' }}>
                    <button
                      onClick={(e) => handleExport(wf.id, e)}
                      title="Export JSON"
                      className={styles.iconBtn}
                    >
                      <Download size={13} />
                    </button>
                    <button
                      onClick={(e) => handleDelete(wf.id, e)}
                      title="Delete"
                      className={styles.iconBtn}
                      style={{ color: 'var(--error)' }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
