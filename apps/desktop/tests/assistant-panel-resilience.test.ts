import { describe, it, expect } from 'vitest';
import React from 'react';
import { renderToString } from 'react-dom/server';
import { ApprovalDialog } from '../src/components/ApprovalDialog';
import { MarkdownRenderer } from '../src/components/chat/MarkdownRenderer';
import { ErrorBoundary } from '../src/components/ErrorBoundary';

describe('Chat Box & Assistant Panel Resilience Tests', () => {
  it('safely renders ApprovalDialog with dictionary/object reason and parameters without throwing', () => {
    const objectReason = {
      status: 'success',
      navigated_to: 'https://fictionhorizon.com/50-best-bollywood-movies-of-all-time-ranked/',
      tier: 'RED TIER'
    };

    const objectParams = {
      selector: 'button.checkout',
      risk_tier: 'RED',
      credentials: { user: 'admin' }
    };

    // Before our fix, calling .includes() or .toUpperCase() on objectReason caused a fatal TypeError.
    let html = '';
    expect(() => {
      html = renderToString(
        React.createElement(ApprovalDialog, {
          isOpen: true,
          actionTitle: 'Authorize Critical Operation',
          reason: objectReason as any,
          toolName: 'navigate',
          parameters: objectParams,
          onApprove: () => {},
          onReject: () => {}
        })
      );
    }).not.toThrow();

    expect(html).toContain('Authorize Critical Operation');
    expect(html).toContain('RED TIER');
    expect(html).toContain('navigate');
  });

  it('safely renders MarkdownRenderer with null, undefined, and non-string inputs', () => {
    let htmlNull = '';
    let htmlUndefined = '';
    let htmlObj = '';

    expect(() => {
      htmlNull = renderToString(React.createElement(MarkdownRenderer, { content: null as any }));
      htmlUndefined = renderToString(React.createElement(MarkdownRenderer, { content: undefined as any }));
      htmlObj = renderToString(React.createElement(MarkdownRenderer, { content: { status: 'running' } as any }));
    }).not.toThrow();

    expect(typeof htmlNull).toBe('string');
    expect(typeof htmlUndefined).toBe('string');
    expect(htmlObj).toContain('running');
  });

  it('renders ErrorBoundary fallback UI when error state is triggered', () => {
    const errorState = ErrorBoundary.getDerivedStateFromError(
      new Error('Simulated runtime render crash in Assistant panel')
    );
    expect(errorState.hasError).toBe(true);
    expect(errorState.error?.message).toContain('Simulated runtime render crash');

    // Create boundary instance and test fallback rendering
    const boundary = new ErrorBoundary({ panelName: 'AI Assistant', children: null });
    boundary.state = {
      hasError: true,
      error: new Error('Simulated runtime render crash in Assistant panel'),
      errorInfo: null,
      showDetails: true
    };

    const rendered = renderToString(boundary.render() as React.ReactElement);
    expect(rendered).toContain('AI Assistant Encountered an Error');
    expect(rendered).toContain('The panel recovered safely to prevent a crash');
    expect(rendered).toContain('Reload Panel');
    expect(rendered).toContain('Simulated runtime render crash');
  });
});
