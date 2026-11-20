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

  // Mask sensitive values from parameter preview for safety
  const sanitizedParams = parameters ? { ...parameters } : {};
  if (sanitizedParams.text && (toolName === 'fill_input' || toolName.includes('password'))) {
    sanitizedParams.text = '•••••••• (Masked for security)';
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
            <div className={styles.title}>{actionTitle}</div>
            <div className={styles.subtitle}>Security Guardrail Active</div>
          </div>
        </div>

        {/* Body */}
        <div className={styles.body}>
          <div className={styles.reasonBox}>
            {reason}
          </div>

          <div className={styles.detailsList}>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Tool:</span>
              <span className={styles.detailValue}>{toolName}</span>
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
