import React, { useState, useEffect } from 'react';
import {
  ListTodo,
  Play,
  RotateCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  Square,
  Bot,
  ShieldAlert,
  Check,
  X
} from 'lucide-react';
import styles from './TaskPanel.module.css';

interface TaskStep {
  id: string;
  step_number: number;
  description: string;
  tool_name?: string;
  status: string;
  result_json?: string;
}

interface TaskItem {
  id: string;
  title: string;
  prompt: string;
  status: string;
  result?: string;
  error?: string;
  created_at: number;
  steps?: TaskStep[];
}

export const TaskPanel: React.FC = () => {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [selectedTask, setSelectedTask] = useState<TaskItem | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState('');
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);

  const loadTasks = async () => {
    if (window.electronAPI?.listTasks) {
      try {
        const list = await window.electronAPI.listTasks();
        setTasks(list || []);
      } catch (err) {
        console.error(err);
      }
    }
  };

  const loadTaskDetails = async (id: string) => {
    if (window.electronAPI?.getTask) {
      try {
        const details = await window.electronAPI.getTask(id);
        setSelectedTask(details);
      } catch (err) {
        console.error(err);
      }
    }
  };

  useEffect(() => {
    loadTasks();
    const interval = setInterval(loadTasks, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedTask?.status === 'running') {
      const interval = setInterval(() => loadTaskDetails(selectedTask.id), 2000);
      return () => clearInterval(interval);
    }
  }, [selectedTask?.id, selectedTask?.status]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || loading) return;

    setLoading(true);
    try {
      const taskTitle = title.trim() || prompt.slice(0, 30);
      if (window.electronAPI?.createTask) {
        const newTask = await window.electronAPI.createTask(taskTitle, prompt);
        setShowCreate(false);
        setTitle('');
        setPrompt('');
        await loadTasks();
        if (newTask?.id) {
          loadTaskDetails(newTask.id);
        }
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (id: string) => {
    if (window.electronAPI?.cancelTask) {
      await window.electronAPI.cancelTask(id);
      loadTasks();
      if (selectedTask?.id === id) {
        loadTaskDetails(id);
      }
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'running':
        return <span className={`${styles.statusBadge} ${styles.statusRunning}`}>Running</span>;
      case 'approval_required':
        return (
          <span
            className={styles.statusBadge}
            style={{
              backgroundColor: 'var(--warning-bg)',
              color: 'var(--warning)',
              border: '1px solid var(--warning)'
            }}
          >
            <ShieldAlert size={10} style={{ display: 'inline', verticalAlign: '-1px', marginRight: '3px' }} />
            Approval Required
          </span>
        );
      case 'completed':
        return <span className={`${styles.statusBadge} ${styles.statusCompleted}`}>Completed</span>;
      case 'failed':
        return <span className={`${styles.statusBadge} ${styles.statusFailed}`}>Failed</span>;
      default:
        return <span className={`${styles.statusBadge} ${styles.statusPending}`}>{status}</span>;
    }
  };

  return (
    <div className={styles.container}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <ListTodo size={14} style={{ color: 'var(--accent-primary)' }} />
          <span style={{ fontSize: '11px', fontWeight: 600, textTransform: 'uppercase' }}>
            Autonomous Tasks ({tasks.length})
          </span>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          style={{
            fontSize: '11px',
            color: 'var(--accent-primary)',
            fontWeight: 600,
            cursor: 'pointer'
          }}
        >
          {showCreate ? 'Cancel' : '+ New Task'}
        </button>
      </div>

      {/* Create Task Form */}
      {showCreate && (
        <form onSubmit={handleCreate} className={styles.createForm}>
          <input
            type="text"
            placeholder="Task Title (optional)"
            className={styles.input}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <textarea
            placeholder="Describe what you want the Autonomous Agent to accomplish (e.g. 'Search for recent quantum computing papers, extract titles, and export to CSV')..."
            className={styles.textarea}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            required
          />
          <button type="submit" disabled={loading || !prompt.trim()} className={styles.submitBtn}>
            <Play size={12} fill="#fff" />
            <span>{loading ? 'Starting...' : 'Launch Agent Task'}</span>
          </button>
        </form>
      )}

      {/* Task List */}
      {tasks.length === 0 && !showCreate ? (
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center', padding: '24px 8px' }}>
          No autonomous agent tasks yet. Click "+ New Task" to delegate a multi-step operation.
        </div>
      ) : (
        <div className={styles.taskList}>
          {tasks.map(t => {
            const isSelected = selectedTask?.id === t.id;
            return (
              <div
                key={t.id}
                onClick={() => loadTaskDetails(t.id)}
                className={`${styles.taskCard} ${isSelected ? styles.taskCardSelected : ''}`}
              >
                <div className={styles.taskHeader}>
                  <span className={styles.taskTitle}>{t.title}</span>
                  {getStatusBadge(t.status)}
                </div>

                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                  {t.prompt.slice(0, 80)}{t.prompt.length > 80 ? '...' : ''}
                </div>

                {/* Expanded Details when selected */}
                {isSelected && selectedTask && (
                  <div style={{ marginTop: '8px', borderTop: '1px solid var(--border-subtle)', paddingTop: '8px' }}>
                    {selectedTask.steps && selectedTask.steps.length > 0 && (
                      <div>
                        <div style={{ fontSize: '10.5px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>
                          Execution Plan ({selectedTask.steps.length} Steps):
                        </div>
                        <div className={styles.stepList}>
                          {selectedTask.steps.map(s => (
                            <div key={s.id} className={styles.stepItem}>
                              <span
                                className={styles.stepDot}
                                style={{
                                  backgroundColor: s.status === 'completed' ? 'var(--success)' :
                                                   s.status === 'running' ? 'var(--accent-primary)' :
                                                   s.status === 'failed' ? 'var(--error)' : 'var(--text-muted)'
                                }}
                              />
                              <div className={styles.stepDesc}>
                                <div>{s.description}</div>
                                {s.tool_name && (
                                  <span style={{ fontSize: '9.5px', color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)' }}>
                                    Tool: {s.tool_name}
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {selectedTask.result && (
                      <div className={styles.resultBox}>
                        <strong>Outcome:</strong> {selectedTask.result}
                      </div>
                    )}

                    {selectedTask.status === 'approval_required' && (
                      <div style={{ display: 'flex', gap: '6px', marginTop: '8px' }}>
                        <button
                          onClick={async (e) => {
                            e.stopPropagation();
                            if (window.electronAPI?.approveTask) {
                              await window.electronAPI.approveTask(selectedTask.id, true);
                              await loadTasks();
                              loadTaskDetails(selectedTask.id);
                            }
                          }}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            backgroundColor: 'var(--success)',
                            color: '#fff',
                            borderRadius: 'var(--radius-sm)',
                            padding: '4px 10px',
                            fontSize: '11px',
                            fontWeight: 600,
                            cursor: 'pointer'
                          }}
                        >
                          <Check size={12} />
                          <span>Approve Action</span>
                        </button>
                        <button
                          onClick={async (e) => {
                            e.stopPropagation();
                            if (window.electronAPI?.rejectTask) {
                              await window.electronAPI.rejectTask(selectedTask.id);
                              await loadTasks();
                              loadTaskDetails(selectedTask.id);
                            }
                          }}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            backgroundColor: 'var(--danger)',
                            color: '#fff',
                            borderRadius: 'var(--radius-sm)',
                            padding: '4px 10px',
                            fontSize: '11px',
                            fontWeight: 600,
                            cursor: 'pointer'
                          }}
                        >
                          <X size={12} />
                          <span>Reject Action</span>
                        </button>
                      </div>
                    )}

                    {selectedTask.status === 'running' && (
                      <div style={{ display: 'flex', gap: '6px', marginTop: '8px' }}>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleCancel(selectedTask.id);
                          }}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            backgroundColor: 'var(--error)',
                            color: '#fff',
                            borderRadius: 'var(--radius-sm)',
                            padding: '3px 8px',
                            fontSize: '10.5px',
                            fontWeight: 600,
                            cursor: 'pointer'
                          }}
                        >
                          <Square size={10} fill="#fff" />
                          <span>Cancel Task</span>
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
