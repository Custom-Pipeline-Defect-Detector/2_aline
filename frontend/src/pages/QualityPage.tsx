import { useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../api'
import { useAuth } from '../auth/AuthContext'
import EditableGrid from '../components/EditableGrid'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import Input from '../components/ui/Input'

interface NCRItem {
  id: number
  project_code?: string
  description: string
  root_cause?: string | null
  corrective_action?: string | null
  status: string
  opened_date?: string | null
  closed_date?: string | null
}

interface InspectionRecord {
  id: number
  project_code?: string
  date: string
  status: string
  summary?: string | null
}

interface InspectionItem {
  id?: number
  label: string
  status?: string
  notes?: string | null
}

function cx(...classes: Array<string | false | undefined | null>) {
  return classes.filter(Boolean).join(' ')
}

function statCount(ncrs: NCRItem[]) {
  const open = ncrs.filter((n) => n.status !== 'closed').length
  const closed = ncrs.filter((n) => n.status === 'closed').length
  return { open, closed, total: ncrs.length }
}

function statusVariant(status: string): 'success' | 'warning' | 'danger' | 'info' {
  const s = (status || '').toLowerCase()
  if (s === 'closed' || s === 'done' || s === 'passed') return 'success'
  if (s === 'open' || s === 'pending' || s === 'in_progress') return 'warning'
  if (s === 'failed' || s === 'blocked' || s === 'rejected') return 'danger'
  return 'info'
}

export default function QualityPage() {
  const [ncrs, setNcrs] = useState<NCRItem[]>([])
  const [inspections, setInspections] = useState<InspectionRecord[]>([])
  const [selectedNcr, setSelectedNcr] = useState<NCRItem | null>(null)
  const [selectedInspection, setSelectedInspection] = useState<InspectionRecord | null>(null)
  const [inspectionItems, setInspectionItems] = useState<InspectionItem[]>([])
  const [savingNcr, setSavingNcr] = useState(false)

  const { can } = useAuth()
  const canWrite = can('qualityWrite')

  const load = async () => {
    const [ncrData, inspectionData] = await Promise.all([
      apiFetch('/ncrs'),
      apiFetch('/inspection-records'),
    ])
    setNcrs(ncrData)
    setInspections(inspectionData)
    if (ncrData.length && !selectedNcr) setSelectedNcr(ncrData[0])
    if (inspectionData.length && !selectedInspection) setSelectedInspection(inspectionData[0])
  }

  const loadInspectionItems = async (recordId?: number) => {
    if (!recordId) {
      setInspectionItems([])
      return
    }
    const data = await apiFetch(`/inspection-records/${recordId}/items`)
    setInspectionItems(data)
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    loadInspectionItems(selectedInspection?.id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedInspection?.id])

  const inspectionColumns = useMemo(
    () => [
      { field: 'label', headerName: 'Checklist item', required: true },
      { field: 'status', headerName: 'Status' },
      { field: 'notes', headerName: 'Notes' },
    ],
    []
  )

  const saveInspectionItems = async (rows: InspectionItem[]) => {
    if (!selectedInspection) return
    const updates = rows.map((row) => {
      if (row.id) {
        return apiFetch(`/inspection-items/${row.id}`, {
          method: 'PATCH',
          body: JSON.stringify(row),
        })
      }
      return apiFetch(`/inspection-records/${selectedInspection.id}/items`, {
        method: 'POST',
        body: JSON.stringify({ ...row, inspection_id: selectedInspection.id }),
      })
    })
    await Promise.all(updates)
    await loadInspectionItems(selectedInspection.id)
  }

  const deleteInspectionItems = async (ids: number[]) => {
    await Promise.all(ids.map((id) => apiFetch(`/inspection-items/${id}`, { method: 'DELETE' })))
    await loadInspectionItems(selectedInspection?.id)
  }

  const updateNcrDetail = async () => {
    if (!selectedNcr) return
    try {
      setSavingNcr(true)
      const updated = await apiFetch(`/ncrs/${selectedNcr.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          root_cause: selectedNcr.root_cause,
          corrective_action: selectedNcr.corrective_action,
          status: selectedNcr.status,
        }),
      })
      setSelectedNcr(updated)
      await load()
    } finally {
      setSavingNcr(false)
    }
  }

  const stats = statCount(ncrs)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700 shadow-sm">
            <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.8)]" />
            Quality Control
          </div>

          <h1 className="mt-3 text-2xl font-semibold text-slate-900">Quality</h1>
          <p className="mt-1 text-sm text-slate-500">
            Manage NCRs, inspections, and corrective actions.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <div className="rounded-2xl bg-white px-4 py-2 text-sm shadow-sm ring-1 ring-slate-900/10">
            <div className="text-[11px] font-medium text-slate-500">Open NCRs</div>
            <div className="text-lg font-semibold text-slate-900">{stats.open}</div>
          </div>
          <div className="rounded-2xl bg-white px-4 py-2 text-sm shadow-sm ring-1 ring-slate-900/10">
            <div className="text-[11px] font-medium text-slate-500">Closed</div>
            <div className="text-lg font-semibold text-slate-900">{stats.closed}</div>
          </div>
          <div className="rounded-2xl bg-white px-4 py-2 text-sm shadow-sm ring-1 ring-slate-900/10">
            <div className="text-[11px] font-medium text-slate-500">Inspections</div>
            <div className="text-lg font-semibold text-slate-900">{inspections.length}</div>
          </div>
        </div>
      </div>

      {/* NCRs + Detail */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* NCR list */}
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold text-slate-900">NCRs</div>
              <div className="text-xs text-slate-500">Select one to view/edit details.</div>
            </div>
            <div className="text-xs text-slate-500">{stats.total} total</div>
          </div>

          {ncrs.length === 0 ? (
            <div className="mt-4 rounded-xl border border-dashed border-slate-200 p-6 text-sm text-slate-400">
              No NCRs logged yet.
            </div>
          ) : (
            <ul className="mt-4 space-y-2">
              {ncrs.map((ncr) => {
                const active = selectedNcr?.id === ncr.id
                const v = statusVariant(ncr.status)

                return (
                  <li key={ncr.id}>
                    <button
                      type="button"
                      onClick={() => setSelectedNcr(ncr)}
                      className={cx(
                        'group relative w-full overflow-hidden rounded-2xl border p-3 text-left',
                        'transition duration-200 active:scale-[0.99]',
                        active ? 'border-emerald-300/50' : 'border-slate-200 hover:border-slate-300'
                      )}
                    >
                      {/* Cyber glow if active */}
                      {active && (
                        <>
                          <span
                            className={cx(
                              'absolute inset-0',
                              'bg-gradient-to-r from-emerald-500/18 via-cyan-400/20 to-fuchsia-500/18',
                              'shadow-[0_0_18px_rgba(16,185,129,0.35)]'
                            )}
                            aria-hidden="true"
                          />
                          <span
                            className={cx(
                              'absolute -inset-1 rounded-2xl blur-xl',
                              'bg-gradient-to-r from-emerald-400/15 via-cyan-400/15 to-fuchsia-400/15',
                              'animate-pulse'
                            )}
                            aria-hidden="true"
                          />
                          {/* Shimmer sweep on hover */}
                          <span className="absolute inset-0 overflow-hidden" aria-hidden="true">
                            <span
                              className={cx(
                                'absolute inset-0',
                                'bg-[linear-gradient(120deg,transparent_0%,rgba(255,255,255,0.16)_45%,transparent_60%)]',
                                'translate-x-[-120%] group-hover:translate-x-[120%]',
                                'transition-transform duration-700 ease-out'
                              )}
                            />
                          </span>
                          <span
                            className={cx(
                              'absolute left-2 top-1/2 h-10 w-1 -translate-y-1/2 rounded-full',
                              'bg-gradient-to-b from-emerald-300 via-cyan-300 to-fuchsia-300',
                              'shadow-[0_0_12px_rgba(34,211,238,0.7)]'
                            )}
                            aria-hidden="true"
                          />
                        </>
                      )}

                      <div className="relative flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-semibold text-slate-900">
                            {ncr.description}
                          </div>
                          <div className="mt-1 text-xs text-slate-500">
                            {ncr.project_code ?? 'Unassigned project'}
                            {ncr.opened_date ? ` · Opened ${ncr.opened_date}` : ''}
                          </div>
                        </div>

                        <div className="shrink-0 text-right">
                          <Badge variant={v}>{ncr.status}</Badge>
                          <div className="mt-1 text-xs text-slate-500">
                            {ncr.status === 'closed' ? ncr.closed_date ?? 'Closed' : 'Open'}
                          </div>
                        </div>
                      </div>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </Card>

        {/* NCR detail */}
        <Card className="p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-slate-900">NCR detail</div>
              <div className="text-xs text-slate-500">Root cause, corrective action, and status.</div>
            </div>
            {selectedNcr ? <Badge variant={statusVariant(selectedNcr.status)}>{selectedNcr.status}</Badge> : null}
          </div>

          {selectedNcr ? (
            <div className="mt-4 space-y-4">
              <div className="rounded-2xl bg-slate-50 p-4 ring-1 ring-slate-900/5">
                <div className="text-xs font-semibold text-slate-600">Selected NCR</div>
                <div className="mt-1 text-sm font-semibold text-slate-900">{selectedNcr.description}</div>
                <div className="mt-1 text-xs text-slate-500">{selectedNcr.project_code ?? 'Unassigned project'}</div>
              </div>

              <div>
                <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Root cause
                </label>
                <Input
                  className="mt-2"
                  disabled={!canWrite}
                  value={selectedNcr.root_cause ?? ''}
                  onChange={(event) => setSelectedNcr({ ...selectedNcr, root_cause: event.target.value })}
                  placeholder="Identify the root cause…"
                />
              </div>

              <div>
                <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Corrective action
                </label>
                <Input
                  className="mt-2"
                  disabled={!canWrite}
                  value={selectedNcr.corrective_action ?? ''}
                  onChange={(event) =>
                    setSelectedNcr({ ...selectedNcr, corrective_action: event.target.value })
                  }
                  placeholder="Define corrective action…"
                />
              </div>

              <div>
                <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Status
                </label>
                <Input
                  className="mt-2"
                  disabled={!canWrite}
                  value={selectedNcr.status}
                  onChange={(event) => setSelectedNcr({ ...selectedNcr, status: event.target.value })}
                  placeholder="open / in_progress / closed…"
                />
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <Button onClick={updateNcrDetail} disabled={!canWrite || savingNcr}>
                  {savingNcr ? 'Saving…' : 'Save NCR detail'}
                </Button>

                {!canWrite ? (
                  <div className="text-xs text-slate-500">
                    You have read-only access.
                  </div>
                ) : null}
              </div>
            </div>
          ) : (
            <div className="mt-4 rounded-xl border border-dashed border-slate-200 p-6 text-sm text-slate-400">
              Select an NCR to edit.
            </div>
          )}
        </Card>
      </div>

      {/* Inspections */}
      <Card className="p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold text-slate-900">Inspection records</div>
            <div className="text-xs text-slate-500">Checklist items are editable below.</div>
          </div>

          <div className="flex items-center gap-2">
            <div className="hidden text-xs font-medium text-slate-500 sm:block">Inspection</div>
            <select
              className={cx(
                'rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm',
                'shadow-sm ring-1 ring-slate-900/5',
                'focus:outline-none focus:ring-2 focus:ring-emerald-400/40'
              )}
              value={selectedInspection?.id ?? ''}
              onChange={(event) => {
                const next = inspections.find((record) => record.id === Number(event.target.value))
                setSelectedInspection(next ?? null)
              }}
            >
              <option value="">Select inspection</option>
              {inspections.map((record) => (
                <option key={record.id} value={record.id}>
                  {record.project_code ?? 'Project'} · {record.date}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-4">
          <EditableGrid
            title="Inspection checklist"
            rows={inspectionItems}
            columns={inspectionColumns}
            onSave={saveInspectionItems}
            onDelete={deleteInspectionItems}
            statusField="status"
            readOnly={!canWrite}
          />
        </div>
      </Card>

      {/* TODO Phase 2: deeper inspection workflows and supplier quality tracking. */}
    </div>
  )
}
