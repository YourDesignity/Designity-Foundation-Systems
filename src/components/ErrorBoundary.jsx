import React from 'react';
import { toast } from '../utils/toast';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
    toast.error('Something went wrong. Please try again.');
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 50, textAlign: 'center' }}>
          <h1 style={{ color: '#ff4d4f' }}>Something went wrong</h1>
          <p>The application encountered an unexpected error. Please refresh.</p>
          <button
            onClick={() => {
              this.setState({ hasError: false });
              window.location.reload();
            }}
            style={{ padding: '10px 20px', cursor: 'pointer' }}
          >
            Refresh Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
