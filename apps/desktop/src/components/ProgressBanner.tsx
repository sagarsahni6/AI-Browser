import React from 'react';
import styles from '../panels/AssistantPanel.module.css';

export interface ProgressBannerProps {
  action?: string;
  stepNumber?: number | string;
  totalSteps?: number | string;
  url?: string;
  query?: string;
  question?: string;
  status?: string;
  parameters?: Record<string, any>;
  children?: React.ReactNode;
}

export const ProgressBanner: React.FC<ProgressBannerProps> = ({
  action,
  stepNumber = '?',
  totalSteps = '?',
  url,
  query,
  question,
  status = 'running',
  parameters,
  children,
}) => {
  if (children) {
    return <>{children}</>;
  }

  const effectiveUrl = url || parameters?.url;
  const effectiveQuery = query || parameters?.query;
  const effectiveQuestion = question || parameters?.question;

  return (
    <div className={`${styles.activeActionBanner} animate-slide-in-down`}>
      <div className={styles.pulseDot} />
      <span style={{ fontWeight: 500 }}>
        Running Step {stepNumber}/{totalSteps}: <strong>{action}</strong>
        {effectiveUrl ? ` (${effectiveUrl})` : ''}
        {effectiveQuery ? ` "${effectiveQuery}"` : ''}
        {effectiveQuestion ? ` (${effectiveQuestion})` : ''}
      </span>
    </div>
  );
};

export default ProgressBanner;
