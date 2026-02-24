import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table'
import Input from '../components/ui/Input'

interface ProjectItem {
  id: number
  project_code: string
  name: string
  status: string
  stage: string
  health: string
  risk?: string | null
}

function cx(...classes: Array<string | false | undefined | null>) {
  return classes.filter(Boolean).join(' ')
}

function healthVariant(health: string) {
  const h = (health || '').toLowerCase()
  if (h === 'red') return 'danger'
  if (h === 'yellow') return 'warning'
  return 'success'
}

function riskVariant(risk?: string | null) {
  const r = (risk || 'low').toLowerCase()
  if (r === 'high') return 'danger'
  if (r === 'medium') return 'warning'
  return 'success'
}

function normalize(s: string) {
  return (s || '').trim().toLowerCase()
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Client-side filters (fast + no backend changes)
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [stageFilter, setStageFilter] = useState<string>('all')
  const [healthFilter, setHealthFilter] = useState<string>('all')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const data = (await apiFetch('/projects')) as ProjectItem[]
      setProjects(Array.isArray(data) ? data : [])
    } catch {
      setError('Unable to load projects. Please retry.')
      setProjects([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const { statuses, stages } = useMemo(() => {
    const st = new Set<string>()
    const sg = new Set<string>()
    for (const p of projects) {
      if (p.status) st.add(p.status)
      if (p.stage) sg.add(p.stage)
    }
    return {
      statuses: Array.from(st).sort((a, b) => a.localeCompare(b)),
      stages: Array.from(sg).sort((a, b) => a.localeCompare(b)),
    }
  }, [projects])

  const filtered = useMemo(() => {
    const q = normalize(query)
    return projects.filter((p) => {
      const matchesQuery =
        !q ||
        normalize(p.project_code).includes(q) ||
        normalize(p.name).includes(q) ||
        normalize(p.stage).includes(q) ||
        normalize(p.status).includes(q)

      const matchesStatus = statusFilter === 'all' || p.status === statusFilter
      const matchesStage = stageFilter === 'all' || p.stage === stageFilter
      const matchesHealth = healthFilter === 'all' || normalize(p.health) === normalize(healthFilter)

      return matchesQuery && matchesStatus && matchesStage && matchesHealth
    })
  }, [projects, query, statusFilter, stageFilter, healthFilter])

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-xs text-slate-500">
          <Link className="font-semibold text-slate-600 hover:underline" to="/dashboard">
            Dashboard
          </Link>{' '}
          <span className="text-slate-400">/</span> <span className="text-slate-700">Projects</span>
        </div>

        <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700 shadow-sm">
          <span className="h-2 w-2 rounded-full bg-sky-400 shadow-[0_0_10px_rgba(56,189,248,0.75)]" />
          Delivery Tracker
        </div>
      </div>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Projects</h1>
          <p className="mt-1 text-sm text-slate-500">Track delivery health and upcoming milestones.</p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => void load()} loading={loading}>
            Refresh
          </Button>
          <Button variant="secondary">New Project</Button>
        </div>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div className="grid flex-1 gap-3 md:grid-cols-3">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Search</div>
              <Input
                className="mt-2"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by code, name, stage, status…"
              />
            </div>

            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Status</div>
              <select
                className={cx(
                  'mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm',
                  'focus:border-emerald-300/60 focus:outline-none focus:ring-2 focus:ring-emerald-400/30'
                )}
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="all">All</option>
                {statuses.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Stage</div>
              <select
                className={cx(
                  'mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm',
                  'focus:border-emerald-300/60 focus:outline-none focus:ring-2 focus:ring-emerald-400/30'
                )}
                value={stageFilter}
                onChange={(e) => setStageFilter(e.target.value)}
              >
                <option value="all">All</option>
                {stages.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 md:mb-1">
              Health
            </div>
            <div className="flex gap-2">
              {(['all', 'green', 'yellow', 'red'] as const).map((h) => (
                <button
                  key={h}
                  type="button"
                  onClick={() => setHealthFilter(h)}
                  className={cx(
                    'rounded-xl border px-3 py-2 text-xs font-semibold transition active:scale-[0.98]',
                    healthFilter === h
                      ? 'border-emerald-300/60 bg-emerald-50 text-emerald-800 shadow-[0_0_18px_rgba(16,185,129,0.18)]'
                      : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                  )}
                >
                  {h === 'all' ? 'All' : h.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
          <div>
            Showing <span className="font-semibold text-slate-700">{filtered.length}</span> of{' '}
            <span className="font-semibold text-slate-700">{projects.length}</span>
          </div>

          {(query || statusFilter !== 'all' || stageFilter !== 'all' || healthFilter !== 'all') ? (
            <button
              type="button"
              className="font-semibold text-slate-700 hover:underline"
              onClick={() => {
                setQuery('')
                setStatusFilter('all')
                setStageFilter('all')
                setHealthFilter('all')
              }}
            >
              Clear filters
            </button>
          ) : null}
        </div>
      </Card>

      {/* Errors */}
      {error ? (
        <Card className="p-6 text-center">
          <p className="text-sm text-slate-600">{error}</p>
          <Button className="mt-4" variant="secondary" onClick={() => void load()}>
            Retry
          </Button>
        </Card>
      ) : null}

      {/* Desktop table */}
      <Card className="hidden overflow-hidden md:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Code</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Stage</TableHead>
              <TableHead>Health</TableHead>
              <TableHead>Risk</TableHead>
              <TableHead>Details</TableHead>
            </TableRow>
          </TableHeader>

          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} className="py-10 text-center text-sm text-slate-500">
                  Loading projects…
                </TableCell>
              </TableRow>
            ) : null}

            {!loading && !error && filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="py-10 text-center text-sm text-slate-500">
                  No matching projects.
                </TableCell>
              </TableRow>
            ) : null}

            {!loading &&
              !error &&
              filtered.map((project) => (
                <TableRow key={project.id}>
                  <TableCell className="font-semibold text-slate-900">{project.project_code}</TableCell>
                  <TableCell className="text-slate-800">{project.name}</TableCell>
                  <TableCell className="text-slate-500">{project.status}</TableCell>
                  <TableCell>
                    <Badge variant="info">{project.stage}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={healthVariant(project.health)} dot>
                      {project.health}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={riskVariant(project.risk)} dot>
                      {project.risk ?? 'low'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Link
                      className="text-xs font-semibold text-slate-700 hover:underline"
                      to={`/projects/${project.id}`}
                    >
                      View
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </Card>

      {/* Mobile cards */}
      <div className="space-y-3 md:hidden">
        {loading ? (
          <>
            {[...Array(5)].map((_, idx) => (
              <div key={idx} className="h-24 animate-pulse rounded-2xl bg-slate-100" />
            ))}
          </>
        ) : null}

        {!loading && !error && filtered.length === 0 ? (
          <Card className="p-8 text-center text-sm text-slate-500">
            No matching projects.
          </Card>
        ) : null}

        {!loading &&
          !error &&
          filtered.map((p) => (
            <Link key={p.id} to={`/projects/${p.id}`} className="block">
              <Card className="group relative overflow-hidden p-4 transition active:scale-[0.99]">
                {/* subtle hover glow */}
                <span
                  className="pointer-events-none absolute -inset-1 rounded-3xl bg-gradient-to-r from-emerald-400/0 via-cyan-400/10 to-fuchsia-400/0 opacity-0 blur-xl transition-opacity duration-300 group-hover:opacity-100"
                  aria-hidden="true"
                />

                <div className="relative">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-slate-900">{p.project_code}</div>
                      <div className="mt-1 truncate text-sm text-slate-700">{p.name}</div>
                      <div className="mt-1 text-xs text-slate-500">
                        {p.status} · {p.stage}
                      </div>
                    </div>

                    <div className="shrink-0 text-right">
                      <Badge variant={healthVariant(p.health)} dot>
                        {p.health}
                      </Badge>
                      <div className="mt-2">
                        <Badge variant={riskVariant(p.risk)}>{p.risk ?? 'low'} risk</Badge>
                      </div>
                    </div>
                  </div>

                  <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
                    <span className="rounded-full bg-slate-100 px-2 py-1">Tap for details</span>
                    <span className="font-semibold text-slate-700">View →</span>
                  </div>
                </div>
              </Card>
            </Link>
          ))}
      </div>

      {/* Big empty state (no projects at all) */}
      {!loading && !error && projects.length === 0 ? (
        <Card className="p-10 text-center text-sm text-slate-500">
          Create a project to start tracking milestones, tasks, and issues.
        </Card>
      ) : null}
    </div>
  )
}
