import React from 'react'
import { AlertTriangle } from 'lucide-react'

// Keeps one broken panel from white-screening the whole terminal.
export default class ErrorBoundary extends React.Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('Panel crashed:', error, info)
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className="m-4 rounded-none border border-red-500/30 bg-red-500/5 p-6">
        <div className="flex items-center gap-2 text-red-400 mb-2">
          <AlertTriangle size={18} />
          <span className="font-bold text-sm">
            {this.props.label || 'This section'} failed to render
          </span>
        </div>
        <p className="text-secondary text-sm mb-3">{this.state.error.message}</p>
        <button
          onClick={() => this.setState({ error: null })}
          className="text-xs px-3 py-1.5 rounded-lg border border-darkBorder hover:bg-darkBorder"
        >
          Retry
        </button>
      </div>
    )
  }
}
