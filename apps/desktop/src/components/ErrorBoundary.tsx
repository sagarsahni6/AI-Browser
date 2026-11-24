import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RotateCcw, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  panelName?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showDetails: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
    showDetails: false,
  };

  public static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`[ErrorBoundary] Uncaught error in ${this.props.panelName || 'panel'}:`, error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReload = () => {
    window.location.reload();
  };

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null, showDetails: false });
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            padding: '24px',
            backgroundColor: 'var(--bg-primary, #ffffff)',
            color: 'var(--text-primary, #1e293b)',
            fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            textAlign: 'center',
            boxSizing: 'border-box',
          }}
        >
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: '50%',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ef4444',
              marginBottom: '16px',
            }}
          >
            <AlertTriangle size={24} />
          </div>

          <h3
            style={{
              margin: '0 0 8px 0',
              fontSize: '15px',
              fontWeight: 600,
              color: 'var(--text-primary, #1e293b)',
            }}
          >
            {this.props.panelName ? `${this.props.panelName} Encountered an Error` : 'Panel Encountered an Error'}
          </h3>

          <p
            style={{
              margin: '0 0 16px 0',
              fontSize: '12px',
              color: 'var(--text-secondary, #64748b)',
              maxWidth: '300px',
              lineHeight: 1.5,
            }}
          >
            The panel recovered safely to prevent a crash. You can reload this view or reset the component state.
          </p>

          <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
            <button
              onClick={this.handleReset}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                fontSize: '12px',
                fontWeight: 500,
                color: 'var(--text-primary, #1e293b)',
                backgroundColor: 'var(--bg-tertiary, #f1f5f9)',
                border: '1px solid var(--border-subtle, #cbd5e1)',
                borderRadius: '6px',
                cursor: 'pointer',
              }}
            >
              <RotateCcw size={13} />
              <span>Retry</span>
            </button>

            <button
              onClick={this.handleReload}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                fontSize: '12px',
                fontWeight: 500,
                color: '#ffffff',
                backgroundColor: 'var(--accent-primary, #3b82f6)',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
              }}
            >
              <RefreshCw size={13} />
              <span>Reload Panel</span>
            </button>
          </div>

          {this.state.error && (
            <div style={{ width: '100%', maxWidth: '340px', textAlign: 'left' }}>
              <button
                type="button"
                onClick={() => this.setState({ showDetails: !this.state.showDetails })}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted, #94a3b8)',
                  fontSize: '11px',
                  cursor: 'pointer',
                  padding: 0,
                  marginBottom: '8px',
                  textDecoration: 'underline',
                }}
              >
                {this.state.showDetails ? 'Hide error details' : 'Show error details'}
              </button>

              {this.state.showDetails && (
                <pre
                  style={{
                    margin: 0,
                    padding: '8px 12px',
                    fontSize: '10px',
                    fontFamily: 'Consolas, monospace',
                    backgroundColor: 'var(--bg-tertiary, #f8fafc)',
                    border: '1px solid var(--border-subtle, #e2e8f0)',
                    borderRadius: '4px',
                    color: '#ef4444',
                    overflowX: 'auto',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    maxHeight: '120px',
                    overflowY: 'auto',
                  }}
                >
                  {this.state.error.message}
                </pre>
              )}
            </div>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
