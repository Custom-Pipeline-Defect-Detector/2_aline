import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { apiFetch } from '../api'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import Input from '../components/ui/Input'
import { useToast } from '../components/Toast'

interface ProposalDetail {
  id: number
  proposed_fields: Record<string, any>
  field_confidence: Record<string, number>
  evidence: Record<string, { snippet?: string; location?: string; source?: string }>
  questions: Record<string, any>
  status: string
  target_table: string
  proposed_action: string
  target_entity_id?: number | null
  doc_version_id: number
}

const formatQuestions = (value: any) => {
  if (!value) return []
  if (Array.isArray(value)) return value.filter(Boolean)
  if (typeof value === 'string') return [value]
  return [JSON.stringify(value)]
}

const entityEndpointByTable: Record<string, string> = {
  customers: '/customers',
  projects: '/projects',
  tasks: '/tasks',
  issues: '/issues',
  ncrs: '/ncrs',
}

const formatValue = (value: any) => {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

export default function ProposalDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const [proposal, setProposal] = useState<ProposalDetail | null>(null)
  const [editedFields, setEditedFields] = useState<Record<string, any>>({})
  const [currentEntity, setCurrentEntity] = useState<Record<string, any> | null>(null)
  const [currentEntityError, setCurrentEntityError] = useState('')
  const [currentEntityLoading, setCurrentEntityLoading] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const draftKey = id ? `proposal-draft-${id}` : ''

  const load = async () => {
    if (!id) return
    setLoading(true)
    setError('')
    try {
      const data = await apiFetch(`/proposals/${id}`)
      setProposal(data)
      const storedDraft = draftKey ? localStorage.getItem(draftKey) : null
      if (storedDraft) {
        setEditedFields(JSON.parse(storedDraft))
      } else {
        setEditedFields(data.proposed_fields || {})
      }
      if (data.target_entity_id && entityEndpointByTable[data.target_table]) {
        setCurrentEntityLoading(true)
        setCurrentEntityError('')
        try {
          const entity = await apiFetch(`${entityEndpointByTable[data.target_table]}/${data.target_entity_id}`)
          setCurrentEntity(entity)
        } catch (entityError) {
          setCurrentEntity(null)
          setCurrentEntityError('Unable to load the current record for comparison.')
        } finally {
          setCurrentEntityLoading(false)
        }
      } else {
        setCurrentEntity(null)
        setCurrentEntityError('')
      }
    } catch (err) {
      setError('Unable to load this proposal. Please retry.')
      setProposal(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [id])

  const updateField = (key: string, value: string) => {
    setEditedFields((current) => {
      const updated = { ...current, [key]: value }
      if (draftKey) {
        localStorage.setItem(draftKey, JSON.stringify(updated))
      }
      return updated
    })
  }

  const evidenceEntries = useMemo(() => Object.entries(proposal?.proposed_fields || {}), [proposal])
  const diffEntries = useMemo(() => {
    if (!currentEntity) return []
    return Object.keys(editedFields || {}).map((key) => ({
      key,
      proposed: editedFields[key],
      current: currentEntity[key],
    }))
  }, [currentEntity, editedFields])

  const handleApprove = async () => {
    if (!proposal) return
    const previousStatus = proposal.status
    setProposal({ ...proposal, status: 'approved' })
    setSaving(true)
    try {
      await apiFetch(`/proposals/${proposal.id}/approve`, {
        method: 'POST',
        body: JSON.stringify({ proposed_fields: editedFields }),
      })
      toast.push({
        title: 'Proposal approved',
        description: `Proposal #${proposal.id} has been approved.`,
        variant: 'success',
      })
      if (draftKey) {
        localStorage.removeItem(draftKey)
      }
      navigate('/inbox')
    } catch (err) {
      setProposal({ ...proposal, status: previousStatus })
      toast.push({
        title: 'Approval failed',
        description: 'Please retry after reviewing the fields.',
        variant: 'error',
      })
    } finally {
      setSaving(false)
    }
  }

  const handleReject = async () => {
    if (!proposal) return
    if (!rejectReason.trim()) {
      toast.push({
        title: 'Reason required',
        description: 'Please add a rejection reason before sending.',
        variant: 'error',
      })
      return
    }
    const previousStatus = proposal.status
    setProposal({ ...proposal, status: 'rejected' })
    setSaving(true)
    try {
      await apiFetch(`/proposals/${proposal.id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason: rejectReason }),
      })
      toast.push({
        title: 'Proposal rejected',
        description: `Proposal #${proposal.id} was rejected.`,
        variant: 'info',
      })
      if (draftKey) {
        localStorage.removeItem(draftKey)
      }
      navigate('/inbox')
    } catch (err) {
      setProposal({ ...proposal, status: previousStatus })
      toast.push({
        title: 'Rejection failed',
        description: 'Please retry after updating the reason.',
        variant: 'error',
      })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <Card className="p-6">
        <div className="text-sm text-slate-500">Loading proposal...</div>
      </Card>
    )
  }

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

  if (!proposal) {
    return (
      <Card className="p-6 text-center">
        <div className="text-sm text-slate-500">Proposal not found.</div>
        <Button className="mt-4" onClick={() => navigate('/inbox')}>
          Back to Inbox
        </Button>
      </Card>
    )
  }

  const handleSaveDraft = () => {
    if (!draftKey) return
    localStorage.setItem(draftKey, JSON.stringify(editedFields))
    toast.push({
      title: 'Draft saved',
      description: 'Your edits are saved locally until you approve.',
      variant: 'success',
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Proposal #{proposal.id}</h1>
          <p className="text-sm text-slate-500">{proposal.proposed_action || `Update ${proposal.target_table}`}</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge
            variant={
              proposal.status === 'approved'
                ? 'success'
                : proposal.status === 'rejected'
                  ? 'danger'
                  : 'warning'
            }
          >
            {proposal.status}
          </Badge>
          <Button variant="ghost" onClick={() => navigate(-1)}>
            Back
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <Card className="p-6">
          <div className="text-sm font-semibold text-slate-900">Proposed fields</div>
          <p className="text-xs text-slate-500">Edit values before approving.</p>
          <div className="mt-4 space-y-4">
            {evidenceEntries.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-200 p-4 text-sm text-slate-400">
                No proposed fields available yet.
              </div>
            ) : null}
            {evidenceEntries.map(([key, value]) => (
              <div key={key} className="rounded-lg border border-slate-100 p-4">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-semibold text-slate-700">{key}</div>
                  <Badge variant="info">Confidence {(proposal.field_confidence?.[key] ?? 0).toFixed(2)}</Badge>
                </div>
                <Input
                  className="mt-3"
                  value={String(editedFields[key] ?? value ?? '')}
                  onChange={(event) => updateField(key, event.target.value)}
                />
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-6">
          <div className="text-sm font-semibold text-slate-900">Evidence & Questions</div>
          <div className="mt-4 space-y-4">
            <div className="rounded-lg border border-slate-100 p-3 text-xs text-slate-500">
              Document version: {proposal.doc_version_id}
            </div>
            {evidenceEntries.length === 0 ? (
              <div className="text-sm text-slate-500">No evidence captured yet.</div>
            ) : null}
            {evidenceEntries.map(([key]) => {
              const evidence = proposal.evidence?.[key]
              const questions = formatQuestions(proposal.questions?.[key])
              return (
                <div key={key} className="rounded-lg border border-slate-100 p-4">
                  <div className="text-sm font-semibold text-slate-700">{key}</div>
                  <div className="mt-2 text-xs text-slate-500">
                    {evidence?.snippet ? `"${evidence.snippet}"` : 'No snippet available.'}
                  </div>
                  {evidence?.source ? (
                    <div className="mt-2 text-xs text-slate-400">Source: {evidence.source}</div>
                  ) : null}
                  {questions.length > 0 ? (
                    <div className="mt-3">
                      <div className="text-xs font-semibold text-slate-500">Questions</div>
                      <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-slate-500">
                        {questions.map((question, index) => (
                          <li key={index}>{question}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              )
            })}
          </div>
        </Card>
      </div>

      <Card className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold text-slate-900">Diff vs current</div>
            <p className="text-xs text-slate-500">Compare AI edits with existing record values.</p>
          </div>
          {proposal.target_entity_id ? (
            <Badge variant="info">Target ID {proposal.target_entity_id}</Badge>
          ) : null}
        </div>
        <div className="mt-4">
          {proposal.target_entity_id ? null : (
            <div className="rounded-lg border border-dashed border-slate-200 p-4 text-sm text-slate-400">
              No current record linked. Approving will create a new record.
            </div>
          )}
          {proposal.target_entity_id && currentEntityLoading ? (
            <div className="text-sm text-slate-500">Loading current record…</div>
          ) : null}
          {proposal.target_entity_id && currentEntityError ? (
            <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-500">
              {currentEntityError}
            </div>
          ) : null}
          {proposal.target_entity_id && currentEntity && diffEntries.length > 0 ? (
            <div className="space-y-3">
              {diffEntries.map((entry) => (
                <div key={entry.key} className="rounded-lg border border-slate-100 p-3">
                  <div className="text-xs font-semibold uppercase text-slate-400">{entry.key}</div>
                  <div className="mt-2 grid gap-2 md:grid-cols-2">
                    <div className="rounded-md bg-slate-50 p-2 text-xs text-slate-600">
                      <div className="text-[10px] uppercase text-slate-400">Current</div>
                      <div className="mt-1">{formatValue(entry.current)}</div>
                    </div>
                    <div className="rounded-md bg-emerald-50 p-2 text-xs text-emerald-700">
                      <div className="text-[10px] uppercase text-emerald-500">Proposed</div>
                      <div className="mt-1">{formatValue(entry.proposed)}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </Card>

      <Card className="p-6">
        <div className="text-sm font-semibold text-slate-900">Decision</div>
        <p className="text-xs text-slate-500">Add a reason for rejection and confirm the next step.</p>
        <textarea
          className="mt-3 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
          rows={3}
          placeholder="Rejection reason (required when rejecting)"
          value={rejectReason}
          onChange={(event) => setRejectReason(event.target.value)}
        />
        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => navigate('/inbox')}>
            Back to Inbox
          </Button>
          <Button variant="ghost" onClick={handleSaveDraft}>
            Save draft edits
          </Button>
          <Button onClick={handleApprove} disabled={saving}>
            Approve
          </Button>
          <Button variant="destructive" onClick={handleReject} disabled={saving}>
            Reject
          </Button>
        </div>
      </Card>
    </div>
  )
}

// TODO Phase 2: feedback-learning loop to capture AI vs human edits for prompt tuning.
