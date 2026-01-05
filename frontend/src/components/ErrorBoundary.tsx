import { Component, ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('React Error Boundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-medieval-navy">
          <div className="bg-parchment-100 p-8 rounded-lg max-w-lg text-center">
            <h1 className="text-2xl font-medieval text-medieval-crimson mb-4">
              Something went wrong
            </h1>
            <p className="text-medieval-stone mb-4">
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-2 bg-medieval-bronze text-white rounded hover:bg-medieval-gold transition-colors"
            >
              Reload Game
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

