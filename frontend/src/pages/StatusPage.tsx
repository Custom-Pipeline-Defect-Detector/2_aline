import { useEffect, useState } from 'react'
import { apiFetch } from '../api'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import { Card } from '../components/ui/Card'

interface StatusResponse {
  db_ok: boolean
  redis_ok: boolean
  worker_ok: boolean
  watcher_ok: boolean
  ollama_ok: boolean
  last_processed_doc?: string | null
  checked_at: string
}

const statusBadge = (ok: boolean) => (ok ? 'success' : 'danger')

export default function StatusPage() {
  const [data, setData] = useState<StatusResponse | null>(null)
  const [error, setError] = useState('')

  const load = async () => {
    setError('')
    try {
      const response = await apiFetch('/status')
      setData(response)
    } catch (err) {
      setError('Unable to load system status.')
    }
  }

  useEffect(() => {
    load()
  }, [])

  if (error) {
    return (
      <Card className="p-6 text-center">
        <div className="text-sm text-slate-500">{error}</div>
        <Button className="mt-4" onClick={load}>
          Retry
        </Button>
      </Card>
    )
  }

  if (!data) {
    return <div className="h-40 animate-pulse rounded-xl bg-slate-100" />
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">System Status</h1>
        <p className="text-sm text-slate-500">Live checks for core services and AI infrastructure.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold text-slate-900">Database</div>
            <Badge variant={statusBadge(data.db_ok)}>{data.db_ok ? 'OK' : 'Down'}</Badge>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold text-slate-900">Redis</div>
            <Badge variant={statusBadge(data.redis_ok)}>{data.redis_ok ? 'OK' : 'Down'}</Badge>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold text-slate-900">Worker</div>
            <Badge variant={statusBadge(data.worker_ok)}>{data.worker_ok ? 'OK' : 'Down'}</Badge>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold text-slate-900">Watcher</div>
            <Badge variant={statusBadge(data.watcher_ok)}>{data.watcher_ok ? 'OK' : 'Down'}</Badge>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold text-slate-900">Ollama</div>
            <Badge variant={statusBadge(data.ollama_ok)}>{data.ollama_ok ? 'OK' : 'Down'}</Badge>
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-xs uppercase text-slate-400">Last processed document</div>
          <div className="mt-2 text-sm text-slate-600">
            {data.last_processed_doc ? new Date(data.last_processed_doc).toLocaleString() : 'No documents processed yet.'}
          </div>
          <div className="mt-2 text-xs text-slate-400">
            Checked at {new Date(data.checked_at).toLocaleString()}
          </div>
        </Card>
      </div>

      {/* TODO Phase 2: drill-down uptime history and alert configuration. */}
    </div>
  )
}
