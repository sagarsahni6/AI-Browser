import React, { useState } from 'react';
import { ShieldAlert, Check, X, Lock, ExternalLink } from 'lucide-react';
import styles from './ApprovalDialog.module.css';

export interface ApprovalDialogProps {
  isOpen: boolean;
  actionTitle?: string;
  reason?: string;
  toolName?: string;
  targetUrl?: string;
  parameters?: Record<string, any>;
  onApprove: (rememberSession: boolean) => void;
  onReject: () => void;
}

export const ApprovalDialog: React.FC<ApprovalDialogProps> = ({
  isOpen,
  actionTitle = 'Sensitive Action Requires Authorization',
  reason = 'The autonomous agent is requesting permission to execute a privileged or sensitive operation.',
  toolName = 'fill_input',
  targetUrl,
  parameters,
  onApprove,
  onReject
}) => {
  const [rememberSession, setRememberSession] = useState(false);
  const [showRawParams, setShowRawParams] = useState(false);

  if (!isOpen) return null;

  // Safe string coercion for reason, actionTitle, and toolName
  const safeReason = typeof reason === 'string' ? reason : (reason ? JSON.stringify(reason) : '');
  const safeTitle = typeof actionTitle === 'string' ? actionTitle : String(actionTitle || '');
  const safeToolName = typeof toolName === 'string' ? toolName : String(toolName || '');

  // Mask sensitive values from parameter preview for safety
  const sanitizedParams = parameters ? { ...parameters } : {};
  if (sanitizedParams.text && (safeToolName === 'fill_input' || safeToolName.includes('password'))) {
    sanitizedParams.text = '•••••••• (Masked for security)';
  }

  // Risk Score Meter calculation
  const normalizedReason = safeReason.toUpperCase();
  const normalizedTitle = safeTitle.toUpperCase();
  const rawTier = String(parameters?.tier || parameters?.risk_tier || '').toUpperCase();

  let tier: 'RED TIER' | 'YELLOW TIER' | 'GREEN TIER' = 'GREEN TIER';
  let percentage = 20;
  let tierColor = 'var(--success, #10b981)';

  if (rawTier.includes('RED') || normalizedReason.includes('RED TIER') || normalizedTitle.includes('RED TIER')) {
    tier = 'RED TIER';
    percentage = 100;
    tierColor = 'var(--error, #ef4444)';
  } else if (rawTier.includes('YELLOW') || normalizedReason.includes('YELLOW TIER') || normalizedTitle.includes('YELLOW TIER')) {
    tier = 'YELLOW TIER';
    percentage = 40;
    tierColor = 'var(--warning, #f59e0b)';
  }

  return (
    <div className={styles.backdrop} onClick={(e) => {
      if (e.target === e.currentTarget) onReject();
    }}>
      <div className={styles.modal} role="dialog" aria-modal="true">
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.iconWrapper}>
            <ShieldAlert size={20} />
          </div>
          <div className={styles.headerContent}>
            <div className={styles.title}>{safeTitle}</div>
            <div className={styles.subtitle}>Security Guardrail Active</div>
          </div>
        </div>

        {/* Body */}
        <div className={styles.body}>
          <div className={styles.reasonBox}>
            {safeReason}
          </div>

          {/* Labeled Color-Coded Risk Score Meter */}
          <div style={{ marginBottom: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px', fontSize: '11px', fontWeight: 600 }}>
              <span style={{ color: 'var(--text-secondary)' }}>Risk Score Assessment</span>
              <span style={{ color: tierColor, fontWeight: 700, letterSpacing: '0.5px' }}>{tier} ({percentage}%)</span>
            </div>
            <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--bg-tertiary, #e2e8f0)', borderRadius: '9999px', overflow: 'hidden' }}>
              <div
                style={{
                  width: `${percentage}%`,
                  height: '100%',
                  backgroundColor: tierColor,
                  borderRadius: '9999px',
                  transition: 'width 0.3s ease, background-color 0.3s ease'
                }}
              />
            </div>
          </div>

          <div className={styles.detailsList}>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Tool:</span>
              <span className={styles.detailValue}>{safeToolName}</span>
            </div>
            {targetUrl && (
              <div className={styles.detailRow}>
                <span className={styles.detailLabel}>Target:</span>
                <span className={styles.detailValue}>{targetUrl}</span>
              </div>
            )}
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Details:</span>
              <button
                type="button"
                onClick={() => setShowRawParams(!showRawParams)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--accent-primary)',
                  cursor: 'pointer',
                  fontSize: '11px',
                  padding: 0
                }}
              >
                {showRawParams ? 'Hide parameters' : 'Inspect parameters'}
              </button>
            </div>
          </div>

          {showRawParams && (
            <div className={styles.paramBox}>
              {JSON.stringify(sanitizedParams, null, 2)}
            </div>
          )}

          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', cursor: 'pointer', color: 'var(--text-secondary)' }}>
            <input
              type="checkbox"
              checked={rememberSession}
              onChange={(e) => setRememberSession(e.target.checked)}
              style={{ cursor: 'pointer' }}
            />
            <span>Remember permission for this browser session</span>
          </label>
        </div>

        {/* Footer */}
        <div className={styles.footer}>
          <button
            type="button"
            className={styles.rejectBtn}
            onClick={onReject}
          >
            <X size={14} style={{ display: 'inline', verticalAlign: '-2px', marginRight: '4px' }} />
            Reject Action
          </button>
          <button
            type="button"
            className={styles.approveBtn}
            onClick={() => onApprove(rememberSession)}
          >
            <Check size={14} style={{ display: 'inline', verticalAlign: '-2px', marginRight: '4px' }} />
            Approve & Continue
          </button>
        </div>
      </div>
    </div>
  );
};
