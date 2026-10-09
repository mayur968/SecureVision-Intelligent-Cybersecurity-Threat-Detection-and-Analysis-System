import React from 'react';

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary] Uncaught error:', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="flex min-h-[200px] flex-col items-center justify-center gap-3 rounded-lg border border-sev-critical/30 bg-sev-critical-bg p-6 text-center">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="#ef4444" strokeWidth="1.5" strokeLinecap="round">
            <circle cx="16" cy="16" r="13" />
            <path d="M16 10v6M16 21v1" />
          </svg>
          <p className="font-semibold text-sev-critical">Something went wrong</p>
          <p className="max-w-sm text-sm text-content-secondary">
            {this.state.error?.message ?? 'An unexpected error occurred.'}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="btn-ghost mt-1 px-4 py-1.5 text-xs"
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
