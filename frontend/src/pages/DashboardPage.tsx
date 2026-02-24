import { useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../api'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import Button from '../components/ui/Button'
import { Card } from '../components/ui/Card'

interface DashboardSummary {
  projects: number
  open_tasks: number
  open_issues: number
  open_ncrs: number
  pending_ai_actions: number
  ncrs_weekly: { week: string; opened: number; closed: number }[]
  tasks_by_status: { status: string; count: number }[]
  projects_by_stage: { stage: string; count: number }[]
}

function cx(...classes: Array<string | false | undefined | null>) {
  return classes.filter(Boolean).join(' ')
}

function StatTile({
  label,
  value,
  icon,
  tone = 'emerald',
}: {
  label: string
  value: number
  icon: string
  tone?: 'emerald' | 'cyan' | 'amber' | 'rose' | 'sky'
}) {
  const toneGlow: Record<typeof tone, string> = {
    emerald: 'from-emerald-500/10 via-cyan-400/10 to-fuchsia-500/10',
    cyan: 'from-cyan-500/10 via-sky-400/10 to-fuchsia-500/10',
    amber: 'from-amber-500/10 via-rose-400/10 to-fuchsia-500/10',
    rose: 'from-rose-500/10 via-amber-400/10 to-fuchsia-500/10',
    sky: 'from-sky-500/10 via-cyan-400/10 to-fuchsia-500/10',
  }

  const dot: Record<typeof tone, string> = {
    emerald: 'bg-emerald-400 shadow-[0_0_12px_rgba(16,185,129,0.7)]',
    cyan: 'bg-cyan-400 shadow-[0_0_12px_rgba(34,211,238,0.7)]',
    amber: 'bg-amber-400 shadow-[0_0_12px_rgba(245,158,11,0.65)]',
    rose: 'bg-rose-400 shadow-[0_0_12px_rgba(244,63,94,0.65)]',
    sky: 'bg-sky-400 shadow-[0_0_12px_rgba(56,189,248,0.65)]',
  }

  return (
    <Card className="group relative overflow-hidden p-4 transition duration-200 hover:-translate-y-[1px]">
      {/* Cyber glow layer */}
      <span
        className={cx(
          'pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100',
          'bg-gradient-to-r',
          toneGlow[tone]
        )}
        aria-hidden="true"
      />
      <span
        className={cx(
          'pointer-events-none absolute -inset-1 rounded-3xl blur-xl opacity-0 transition-opacity duration-300 group-hover:opacity-100',
          'bg-gradient-to-r',
          toneGlow[tone]
        )}
        aria-hidden="true"
      />

      <div className="relative flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
          <div className="mt-2 text-2xl font-semibold text-slate-900">{value}</div>
        </div>

        <div className="relative grid h-11 w-11 place-items-center rounded-2xl bg-slate-50 ring-1 ring-slate-900/5">
          <span className="text-lg">{icon}</span>
          <span className={cx('absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full', dot[tone])} />
        </div>
      </div>
    </Card>
  )
}

function ChartShell({
  title,
  subtitle,
  children,
  empty,
}: {
  title: string
  subtitle?: string
  empty?: boolean
  children: React.ReactNode
}) {
  return (
    <div className="space-y-2">
      <div>
        <div className="text-sm font-semibold text-slate-900">{title}</div>
        {subtitle ? <div className="text-xs text-slate-500">{subtitle}</div> : null}
      </div>

      <div className="h-64">
        {empty ? (
          <div className="flex h-full items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50 text-sm text-slate-500">
            No data available yet.
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const response = (await apiFetch('/dashboard/summary')) as DashboardSummary
      setData(response)
    } catch {
      setError('Unable to load dashboard summary. Please check your connection and try again.')
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const hasCharts = useMemo(() => {
    if (!data) return false
    return (
      (data.ncrs_weekly?.length ?? 0) > 0 ||
      (data.tasks_by_status?.length ?? 0) > 0 ||
      (data.projects_by_stage?.length ?? 0) > 0
    )
  }, [data])

  if (error) {
    return (
      <Card className="p-6 text-center">
        <p className="text-sm text-slate-600">{error}</p>
        <Button className="mt-4" onClick={() => void load()}>
          Retry
        </Button>
      </Card>
    )
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="h-5 w-48 animate-pulse rounded bg-slate-200" />
            <div className="mt-2 h-4 w-80 animate-pulse rounded bg-slate-100" />
          </div>
          <div className="h-10 w-28 animate-pulse rounded-xl bg-slate-100" />
        </div>

        <div className="grid gap-4 md:grid-cols-5">
          {[...Array(5)].map((_, idx) => (
            <div key={idx} className="h-28 animate-pulse rounded-2xl bg-slate-100" />
          ))}
        </div>

        <div className="h-[420px] animate-pulse rounded-2xl bg-slate-100" />
      </div>
    )
  }

  if (!data) {
    return (
      <Card className="p-6 text-center">
        <p className="text-sm text-slate-600">No dashboard data is available yet.</p>
        <Button className="mt-4" variant="secondary" onClick={() => void load()}>
          Retry
        </Button>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700 shadow-sm">
            <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.8)]" />
            Ops Overview
          </div>
          <h1 className="mt-3 text-2xl font-semibold text-slate-900">Dashboard</h1>
          <p className="mt-1 text-sm text-slate-500">Key operational signals across projects, quality, and AI.</p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => void load()}>
            Refresh
          </Button>
        </div>
      </div>

      {/* KPI Tiles */}
      <div className="grid gap-4 md:grid-cols-5">
        <StatTile label="Projects" value={data.projects} icon="📌" tone="sky" />
        <StatTile label="Open Tasks" value={data.open_tasks} icon="✅" tone="emerald" />
        <StatTile label="Open Issues" value={data.open_issues} icon="🚩" tone="amber" />
        <StatTile label="Open NCR" value={data.open_ncrs} icon="🛠️" tone="rose" />
        <StatTile label="Pending AI Actions" value={data.pending_ai_actions} icon="🤖" tone="cyan" />
      </div>

      {/* Charts */}
      <Card className="p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="text-sm font-semibold text-slate-900">Trends & breakdowns</div>
            <div className="text-xs text-slate-500">Weekly NCRs, tasks distribution, project pipeline stages.</div>
          </div>

          {!hasCharts ? (
            <div className="text-xs text-slate-500">No chart data yet.</div>
          ) : null}
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <ChartShell
            title="NCRs opened vs closed"
            subtitle="Weekly trend"
            empty={(data.ncrs_weekly?.length ?? 0) === 0}
          >
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.ncrs_weekly}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="week" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="opened" stroke="#ef4444" name="Opened" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="closed" stroke="#22c55e" name="Closed" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </ChartShell>

          <ChartShell
            title="Tasks by status"
            subtitle="Current snapshot"
            empty={(data.tasks_by_status?.length ?? 0) === 0}
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.tasks_by_status}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="status" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#3b82f6" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartShell>

          <ChartShell
            title="Projects by stage"
            subtitle="Pipeline distribution"
            empty={(data.projects_by_stage?.length ?? 0) === 0}
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.projects_by_stage}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="stage" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#0f766e" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartShell>
        </div>
      </Card>
    </div>
  )
}
