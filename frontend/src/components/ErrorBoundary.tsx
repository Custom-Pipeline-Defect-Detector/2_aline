import React from 'react'
import { useNavigate } from 'react-router-dom'
import Button from './ui/Button'

type State = { hasError: boolean; error?: Error }

class ErrorBoundaryInner extends React.Component<{ onReset: () => void }, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error) {
    console.error('UI render error', error)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-[60vh] items-center justify-center px-6">
          <div className="max-w-lg rounded-xl border border-slate-200 bg-white p-6 text-center shadow-sm">
            <div className="text-lg font-semibold text-slate-900">Something went wrong</div>
            <p className="mt-2 text-sm text-slate-500">
              The page ran into an unexpected issue. Please return to the dashboard and try again.
            </p>
            <Button className="mt-4" onClick={this.props.onReset}>
              Back to Dashboard
            </Button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export default function ErrorBoundary({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  return <ErrorBoundaryInner onReset={() => navigate('/dashboard')}>{children}</ErrorBoundaryInner>
}
