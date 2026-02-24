import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiFetch } from '../api'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import Input from '../components/ui/Input'
import EditableGrid from '../components/EditableGrid'

interface ProjectDetail {
  id: number
  project_code: string
  name: string
  status: string
  stage: string
  value_amount?: number | null
  currency?: string
  health: string
  risk?: string | null
  start_date?: string | null
  due_date?: string | null
  tasks: { id: number; title: string; status: string }[]
  issues: { id: number; description: string; severity: string }[]
  ncrs: { id: number; description: string; status: string }[]
  recent_documents: { id: number; filename: string; created_at: string; processing_status: string }[]
  pending_ai_actions: number
}

interface Milestone {
  id: number
  name: string
  due_date?: string | null
  status: string
}

interface TaskDetail {
  id: number
  title: string
  status: string
}

interface BomItem {
  id?: number
  part_no: string
  name: string
  qty: number
  supplier?: string | null
  lead_time_days?: number | null
  status?: string
}

interface AuditEntry {
  id: number
  action: string
  created_at: string
  before?: Record<string, any>
  after?: Record<string, any>
}

const STAGES = ['intake', 'scope', 'design', 'procurement', 'manufacturing', 'assembly', 'commissioning', 'delivery'] as const
const STATUS_OPTIONS = ['active', 'on_hold', 'closed', 'cancelled'] as const
const HEALTH_OPTIONS = ['green', 'yellow', 'red'] as const
const RISK_OPTIONS = ['low', 'medium', 'high'] as const
const CURRENCY_OPTIONS = ['USD', 'EUR', 'GBP', 'INR', 'AED'] as const

function cx(...classes: Array<string | false | undefined | null>) {
  return classes.filter(Boolean).join(' ')
}

function withCurrent(options: readonly string[], current?: string | null) {
  const cur = (current || '').trim()
  if (!cur) return options
  return options.includes(cur) ? options : [cur, ...options]
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

function severityVariant(sev: string) {
  const s = (sev || '').toLowerCase()
  if (s === 'critical' || s === 'high') return 'danger'
  if (s === 'medium') return 'warning'
  return 'info'
}

// backend appears to store dates like "YYYY-MM-DD" (based on your current code).
// Keep it that way so we don't break saving.
// This also shows a native calendar picker in browsers.
function toDateInputValue(value?: string | null) {
  if (!value) return ''
  // If backend ever sends ISO, take the date part.
  const iso = value.includes('T') ? value.split('T')[0] : value
  return iso.slice(0, 10)
}

export default function ProjectDetailPage() {
  const { id } = useParams()

  const [project, setProject] = useState<ProjectDetail | null>(null)
  const [draft, setDraft] = useState<ProjectDetail | null>(null)

  const [milestones, setMilestones] = useState<Milestone[]>([])
  const [tasks, setTasks] = useState<TaskDetail[]>([])
  const [bomItems, setBomItems] = useState<BomItem[]>([])
  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([])

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const startDateRef = useRef<HTMLInputElement | null>(null)
  const dueDateRef = useRef<HTMLInputElement | null>(null)

  const load = async () => {
    if (!id) return
    setLoading(true)
    try {
      const data = (await apiFetch(`/projects/${id}`)) as ProjectDetail
      setProject(data)
      setDraft(data)

      const [milestoneData, taskData, bomData, auditData] = await Promise.all([
        apiFetch(`/projects/${id}/milestones`),
        apiFetch(`/tasks?project_id=${id}`),
        apiFetch(`/projects/${id}/bom-items`),
        apiFetch(`/audit?entity_type=projects&entity_id=${id}`),
      ])

      setMilestones(milestoneData)
      setTasks(taskData)
      setBomItems(bomData)
      setAuditEntries(auditData)
    } catch {
      setProject(null)
      setDraft(null)
      setMilestones([])
      setTasks([])
      setBomItems([])
      setAuditEntries([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  const saveProject = async () => {
    if (!id || !draft) return
    setSaving(true)
    try {
      const payload = {
        name: draft.name,
        status: draft.status,
        stage: draft.stage,
        value_amount: draft.value_amount ?? null,
        currency: draft.currency ?? null,
        health: draft.health,
        risk: draft.risk ?? null,
        // keep as date strings "YYYY-MM-DD" (safe)
        start_date: draft.start_date ? toDateInputValue(draft.start_date) : null,
        due_date: draft.due_date ? toDateInputValue(draft.due_date) : null,
      }

      const updated = (await apiFetch(`/projects/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      })) as ProjectDetail

      setProject(updated)
      setDraft(updated)

      // optional: refresh related data (milestones/tasks/bom/audit) if backend updates them
      // await load()
    } finally {
      setSaving(false)
    }
  }

  const bomColumns = useMemo(
    () => [
      { field: 'part_no', headerName: 'Part no', required: true },
      { field: 'name', headerName: 'Name', required: true },
      { field: 'qty', headerName: 'Qty', required: true },
      { field: 'supplier', headerName: 'Supplier' },
      { field: 'lead_time_days', headerName: 'Lead time' },
      { field: 'status', headerName: 'Status' },
    ],
    []
  )

  const saveBomItems = async (rows: BomItem[]) => {
    if (!id) return
    const updates = rows.map((row) => {
      if (row.id) return apiFetch(`/bom-items/${row.id}`, { method: 'PATCH', body: JSON.stringify(row) })
      return apiFetch(`/projects/${id}/bom-items`, { method: 'POST', body: JSON.stringify(row) })
    })
    await Promise.all(updates)
    const next = await apiFetch(`/projects/${id}/bom-items`)
    setBomItems(next)
  }

  const deleteBomItems = async (ids: number[]) => {
    await Promise.all(ids.map((itemId) => apiFetch(`/bom-items/${itemId}`, { method: 'DELETE' })))
    const next = await apiFetch(`/projects/${id}/bom-items`)
    setBomItems(next)
  }

  const groupedTasks = useMemo(() => {
    const groups: Record<string, TaskDetail[]> = { open: [], in_progress: [], blocked: [], done: [] }
    tasks.forEach((task) => {
      const key = groups[task.status] ? task.status : 'open'
      groups[key].push(task)
    })
    return groups
  }, [tasks])

  const updateTaskStatus = async (task: TaskDetail, status: string) => {
    const updated = await apiFetch(`/tasks/${task.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    })
    setTasks((current) => current.map((item) => (item.id === updated.id ? updated : item)))
  }

  if (loading) {
    return (
      <Card className="p-6">
        <div className="text-sm text-slate-500">Loading project…</div>
      </Card>
    )
  }

  if (!project || !draft) {
    return (
      <Card className="p-6 text-center">
        <div className="text-sm text-slate-500">Project not found.</div>
        <Button className="mt-4" onClick={() => window.history.back()}>
          Back
        </Button>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-xs text-slate-500">
          <Link className="font-semibold text-slate-700 hover:underline" to="/projects">
            Projects
          </Link>{' '}
          <span className="text-slate-400">/</span> <span className="text-slate-900">{project.project_code}</span>
        </div>

        <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700 shadow-sm">
          <span className="h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.75)]" />
          Project Command
        </div>
      </div>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="truncate text-2xl font-semibold text-slate-900">{project.project_code}</h1>
          <p className="mt-1 truncate text-sm text-slate-500">{project.name}</p>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Badge variant="info">{project.stage}</Badge>
            <Badge variant={healthVariant(project.health)} dot>
              {project.health}
            </Badge>
            <Badge variant={riskVariant(project.risk)} dot>
              {project.risk ?? 'low'} risk
            </Badge>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => void load()} loading={loading}>
            Refresh
          </Button>
          <Button onClick={saveProject} loading={saving}>
            Save changes
          </Button>
        </div>
      </div>

      {/* Details */}
      <Card className="p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold text-slate-900">Project details</div>
            <div className="text-xs text-slate-500">Dropdowns for selectable fields + calendar date picker.</div>
          </div>
          <div className="text-xs text-slate-500">ID: #{project.id}</div>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {/* Name */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Name</label>
            <Input
              className="mt-2"
              value={draft.name || ''}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            />
          </div>

          {/* Stage dropdown */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Stage</label>
            <select
              className={cx(
                'mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm',
                'focus:border-emerald-300/60 focus:outline-none focus:ring-2 focus:ring-emerald-400/30'
              )}
              value={draft.stage || ''}
              onChange={(e) => setDraft({ ...draft, stage: e.target.value })}
            >
              {withCurrent(STAGES as unknown as readonly string[], draft.stage).map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          {/* Status dropdown */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Status</label>
            <select
              className={cx(
                'mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm',
                'focus:border-emerald-300/60 focus:outline-none focus:ring-2 focus:ring-emerald-400/30'
              )}
              value={draft.status || ''}
              onChange={(e) => setDraft({ ...draft, status: e.target.value })}
            >
              {withCurrent(STATUS_OPTIONS as unknown as readonly string[], draft.status).map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          {/* Health dropdown */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Health</label>
            <select
              className={cx(
                'mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm',
                'focus:border-emerald-300/60 focus:outline-none focus:ring-2 focus:ring-emerald-400/30'
              )}
              value={(draft.health || '').toLowerCase()}
              onChange={(e) => setDraft({ ...draft, health: e.target.value })}
            >
              {withCurrent(HEALTH_OPTIONS as unknown as readonly string[], (draft.health || '').toLowerCase()).map(
                (s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                )
              )}
            </select>
          </div>

          {/* Risk dropdown */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Risk</label>
            <select
              className={cx(
                'mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm',
                'focus:border-emerald-300/60 focus:outline-none focus:ring-2 focus:ring-emerald-400/30'
              )}
              value={(draft.risk || 'low').toLowerCase()}
              onChange={(e) => setDraft({ ...draft, risk: e.target.value })}
            >
              {withCurrent(RISK_OPTIONS as unknown as readonly string[], (draft.risk || 'low').toLowerCase()).map(
                (s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                )
              )}
            </select>
          </div>

          {/* Value amount */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Value amount</label>
            <Input
              className="mt-2"
              value={draft.value_amount ?? ''}
              onChange={(e) =>
                setDraft({ ...draft, value_amount: e.target.value ? Number(e.target.value) : null })
              }
            />
          </div>

          {/* Currency dropdown */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Currency</label>
            <select
              className={cx(
                'mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm',
                'focus:border-emerald-300/60 focus:outline-none focus:ring-2 focus:ring-emerald-400/30'
              )}
              value={(draft.currency || '').toUpperCase()}
              onChange={(e) => setDraft({ ...draft, currency: e.target.value })}
            >
              {withCurrent(CURRENCY_OPTIONS as unknown as readonly string[], (draft.currency || '').toUpperCase()).map(
                (s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                )
              )}
            </select>
          </div>

          {/* Start date (calendar) */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Start date</label>
            <div className="mt-2 flex gap-2">
              <Input
                ref={startDateRef}
                type="date"
                value={toDateInputValue(draft.start_date)}
                onChange={(e) => setDraft({ ...draft, start_date: e.target.value || null })}
              />
              <button
                type="button"
                className="grid h-[42px] w-[42px] place-items-center rounded-xl border border-slate-200 bg-white text-slate-700 shadow-sm transition hover:bg-slate-50 active:scale-[0.98]"
                onClick={() => {
                  const el = startDateRef.current as any
                  if (el?.showPicker) el.showPicker()
                  else startDateRef.current?.focus()
                }}
                aria-label="Open calendar"
              >
                📅
              </button>
            </div>
          </div>

          {/* Due date (calendar) */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Due date</label>
            <div className="mt-2 flex gap-2">
              <Input
                ref={dueDateRef}
                type="date"
                value={toDateInputValue(draft.due_date)}
                onChange={(e) => setDraft({ ...draft, due_date: e.target.value || null })}
              />
              <button
                type="button"
                className="grid h-[42px] w-[42px] place-items-center rounded-xl border border-slate-200 bg-white text-slate-700 shadow-sm transition hover:bg-slate-50 active:scale-[0.98]"
                onClick={() => {
                  const el = dueDateRef.current as any
                  if (el?.showPicker) el.showPicker()
                  else dueDateRef.current?.focus()
                }}
                aria-label="Open calendar"
              >
                📅
              </button>
            </div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <Button onClick={saveProject} loading={saving}>
            Save changes
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              setDraft(project)
            }}
            disabled={saving}
          >
            Reset
          </Button>
        </div>
      </Card>

      {/* Stage timeline */}
      <Card className="p-4">
        <div className="text-sm font-semibold text-slate-900">Stage timeline</div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {STAGES.map((stage) => {
            const isCurrent = stage === project.stage
            const due =
              milestones.find((m) => (m.name || '').toLowerCase().includes(stage))?.due_date ?? null

            return (
              <div
                key={stage}
                className={cx(
                  'group relative overflow-hidden rounded-2xl border p-3 text-sm transition',
                  isCurrent ? 'border-emerald-300/60 bg-emerald-50/30' : 'border-slate-200 bg-white',
                  'hover:border-slate-300'
                )}
              >
                {isCurrent ? (
                  <span
                    className="pointer-events-none absolute -inset-1 rounded-3xl bg-gradient-to-r from-emerald-400/0 via-cyan-400/12 to-fuchsia-400/0 blur-xl"
                    aria-hidden="true"
                  />
                ) : null}

                <div className="relative flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="font-semibold text-slate-800">{stage}</div>
                    <div className="mt-1 text-xs text-slate-500">{due ?? 'No date'}</div>
                  </div>
                  {isCurrent ? (
                    <span className="rounded-full bg-cyan-50 px-2 py-1 text-[11px] font-semibold text-cyan-700 ring-1 ring-cyan-200">
                      Current
                    </span>
                  ) : (
                    <span className="rounded-full bg-slate-50 px-2 py-1 text-[11px] font-semibold text-slate-600 ring-1 ring-slate-200">
                      Next
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </Card>

      {/* Boards */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Milestones */}
        <Card className="p-4">
          <div className="text-sm font-semibold text-slate-900">Milestones</div>
          {milestones.length === 0 ? (
            <div className="mt-3 rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
              No milestones yet.
            </div>
          ) : (
            <ul className="mt-3 space-y-2 text-sm">
              {milestones.map((m) => (
                <li key={m.id} className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-3">
                  <div className="min-w-0">
                    <div className="font-semibold text-slate-800">{m.name}</div>
                    <div className="text-xs text-slate-500">{m.status}</div>
                  </div>
                  <div className="text-xs font-semibold text-slate-600">{m.due_date ?? 'TBD'}</div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* Task board */}
        <Card className="p-4">
          <div className="text-sm font-semibold text-slate-900">Task board</div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(groupedTasks).map(([status, items]) => (
              <div key={status} className="rounded-2xl border border-slate-200 bg-white p-3">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{status}</div>
                <div className="mt-2 space-y-2">
                  {items.length === 0 ? (
                    <div className="text-xs text-slate-400">No tasks</div>
                  ) : (
                    items.map((task) => (
                      <div key={task.id} className="rounded-2xl border border-slate-200 bg-white p-2">
                        <div className="font-medium text-slate-800">{task.title}</div>
                        <div className="mt-2 flex flex-wrap gap-1 text-xs">
                          {['open', 'in_progress', 'blocked', 'done'].map((next) => {
                            const active = next === task.status
                            return (
                              <button
                                key={next}
                                type="button"
                                className={cx(
                                  'rounded-full px-2 py-0.5 font-semibold transition active:scale-[0.98]',
                                  active ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                                )}
                                onClick={() => void updateTaskStatus(task, next)}
                              >
                                {next}
                              </button>
                            )
                          })}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Issues */}
        <Card className="p-4">
          <div className="text-sm font-semibold text-slate-900">Issues</div>
          {project.issues.length === 0 ? (
            <div className="mt-3 rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
              No open issues.
            </div>
          ) : (
            <ul className="mt-3 space-y-2 text-sm">
              {project.issues.map((issue) => (
                <li key={issue.id} className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-3">
                  <div className="min-w-0">
                    <div className="truncate font-medium text-slate-800">{issue.description}</div>
                    <div className="text-xs text-slate-500">Issue #{issue.id}</div>
                  </div>
                  <Badge variant={severityVariant(issue.severity)} dot>
                    {issue.severity}
                  </Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* NCRs */}
        <Card className="p-4">
          <div className="text-sm font-semibold text-slate-900">NCRs</div>
          {project.ncrs.length === 0 ? (
            <div className="mt-3 rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
              No NCRs logged.
            </div>
          ) : (
            <ul className="mt-3 space-y-2 text-sm">
              {project.ncrs.map((ncr) => (
                <li key={ncr.id} className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-3">
                  <div className="min-w-0">
                    <div className="truncate font-medium text-slate-800">{ncr.description}</div>
                    <div className="text-xs text-slate-500">NCR #{ncr.id}</div>
                  </div>
                  <Badge variant={ncr.status === 'closed' ? 'success' : 'warning'} dot>
                    {ncr.status}
                  </Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* Latest documents */}
        <Card className="p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-slate-900">Latest documents</div>
              <div className="text-xs text-slate-500">Most recent uploads for this project.</div>
            </div>
            <Badge variant="info" dot>
              {project.pending_ai_actions} AI pending
            </Badge>
          </div>

          {project.recent_documents.length === 0 ? (
            <div className="mt-3 rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
              No recent documents.
            </div>
          ) : (
            <ul className="mt-3 space-y-2 text-sm">
              {project.recent_documents.map((doc) => (
                <li key={doc.id} className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-3">
                  <div className="min-w-0">
                    <div className="truncate font-medium text-slate-800">{doc.filename}</div>
                    <div className="text-xs text-slate-500">{new Date(doc.created_at).toLocaleString()}</div>
                  </div>
                  <Badge variant="default">{doc.processing_status}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {/* BOM */}
      <Card className="p-4">
        <EditableGrid
          title="BOM items"
          rows={bomItems}
          columns={bomColumns}
          onSave={saveBomItems}
          onDelete={deleteBomItems}
          statusField="status"
        />
      </Card>

      {/* History */}
      <Card className="p-4">
        <div className="text-sm font-semibold text-slate-900">History</div>
        {auditEntries.length === 0 ? (
          <div className="mt-3 rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
            No history recorded yet.
          </div>
        ) : (
          <ul className="mt-3 space-y-2 text-sm">
            {auditEntries.map((entry) => (
              <li key={entry.id} className="rounded-2xl border border-slate-200 bg-white p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold text-slate-800">{entry.action}</span>
                  <span className="text-xs text-slate-500">{new Date(entry.created_at).toLocaleString()}</span>
                </div>
                <div className="mt-2 grid gap-2 md:grid-cols-2">
                  <div className="rounded-xl bg-slate-50 p-2 text-xs text-slate-600 ring-1 ring-slate-900/5">
                    <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Before</div>
                    <div className="mt-1 break-words">{JSON.stringify(entry.before ?? {})}</div>
                  </div>
                  <div className="rounded-xl bg-slate-50 p-2 text-xs text-slate-600 ring-1 ring-slate-900/5">
                    <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">After</div>
                    <div className="mt-1 break-words">{JSON.stringify(entry.after ?? {})}</div>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
