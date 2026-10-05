import React, { Component } from 'react';

/**
 * Global error boundary for the adjudicator portal.
 * Catches rendering errors in child components and displays a fallback UI.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    // Log the error – in a real app you might send this to a monitoring service.
    console.error('Adjudicator portal error:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary" style={{ padding: 40, fontFamily: 'Poppins, sans-serif' }}>
          <h2>Something went wrong.</h2>
          <pre>{this.state.error?.toString()}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}
