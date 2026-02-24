import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, apiFetch, buildApiUrl, reprocessDocument } from '../api'
import { useAuth } from '../auth/AuthContext'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table'
import { useToast } from '../components/Toast'

interface DocumentItem {
  id: number
  filename: string
  mime: string
  storage_path: string
  file_hash: string
  processing_status: string
  document_type?: string
  needs_review: boolean
  agent_summary?: string
  extracted_fields?: Record<string, any>
  customer_name?: string | null
  project_name?: string | null
  versions?: { id: number; version: number; created_at: string }[]
  proposals?: { id: number; status: string; proposed_action: string; target_table: string; created_at: string }[]
  created_at: string
  processing_error?: string
}

const DOCUMENT_TYPE_OPTIONS = [
  'po',
  'invoice',
  'sow',
  'contract',
  'spec',
  'drawing',
  'email',
  'other',
] as const

function cx(...classes: Array<string | false | undefined | null>) {
  return classes.filter(Boolean).join(' ')
}


function getLowConfidenceFields(extractedFields?: Record<string, any>): string[] {
  if (!extractedFields || typeof extractedFields !== 'object') return []
  const confidence = extractedFields?._confidence
  if (!confidence || typeof confidence !== 'object') return []

  return Object.entries(confidence)
    .filter(([, value]) => typeof value === 'number' && value < 0.6)
    .map(([key]) => key)
}

function statusVariant(status: string) {
  if (status === 'failed') return 'danger'
  if (status === 'processing' || status === 'queued') return 'warning'
  if (status === 'done') return 'success'
  return 'default'
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [file, setFile] = useState<File | null>(null)
  const [expanded, setExpanded] = useState<number | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(false)

  const [editValues, setEditValues] = useState<
    Record<
      number,
      { document_type: string; agent_summary: string; extracted_fields: string; needs_review: boolean }
    >
  >({})

  const [jsonErrors, setJsonErrors] = useState<Record<number, string>>({})
  const [savingDocId, setSavingDocId] = useState<number | null>(null)
  const autoSaveTimers = useRef<Record<number, number>>({})
  const autoSaveInFlight = useRef<Record<number, boolean>>({})

  const toast = useToast()
  const { can } = useAuth()
  const canWrite = can('documentsWrite')

  const loadDocs = async () => {
    try {
      const data = (await apiFetch('/documents')) as DocumentItem[]
      setDocuments(data)
    } catch {
      setDocuments([])
    }
  }

  useEffect(() => {
    void loadDocs()
  }, [])

  const ensureEditValues = (doc: DocumentItem) => {
    setEditValues((current) => {
      if (current[doc.id]) return current
      return {
        ...current,
        [doc.id]: {
          document_type: doc.document_type ?? '',
          agent_summary: doc.agent_summary ?? '',
          extracted_fields: JSON.stringify(doc.extracted_fields ?? {}, null, 2),
          needs_review: doc.needs_review,
        },
      }
    })
  }

  const updateEditField = (docId: number, field: string, value: string | boolean) => {
    setEditValues((current) => ({
      ...current,
      [docId]: {
        document_type: current[docId]?.document_type ?? '',
        agent_summary: current[docId]?.agent_summary ?? '',
        extracted_fields: current[docId]?.extracted_fields ?? '{}',
        needs_review: current[docId]?.needs_review ?? false,
        [field]: value,
      },
    }))
  }

  const validateJson = (docId: number) => {
    const raw = editValues[docId]?.extracted_fields ?? '{}'
    try {
      JSON.parse(raw || '{}')
      setJsonErrors((cur) => {
        const next = { ...cur }
        delete next[docId]
        return next
      })
      return true
    } catch (e: any) {
      setJsonErrors((cur) => ({ ...cur, [docId]: 'Extracted fields must be valid JSON.' }))
      return false
    }
  }

  const saveEdits = async (doc: DocumentItem, options?: { silent?: boolean }) => {
    const values = editValues[doc.id]
    if (!values) return

    if (!validateJson(doc.id)) {
      if (!options?.silent) {
        toast.push({ title: 'Invalid JSON', description: 'Fix JSON before saving.', variant: 'error' })
      }
      return
    }

    let parsedFields: Record<string, any> = {}
    try {
      parsedFields = values.extracted_fields ? JSON.parse(values.extracted_fields) : {}
    } catch {
      if (!options?.silent) {
        toast.push({ title: 'Invalid JSON', description: 'Extracted fields must be valid JSON.', variant: 'error' })
      }
      return
    }

    setSavingDocId(doc.id)
    try {
      await apiFetch(`/documents/${doc.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          document_type: values.document_type || null,
          agent_summary: values.agent_summary || null,
          extracted_fields: parsedFields,
          needs_review: values.needs_review,
        }),
      })

      if (!options?.silent) {
        toast.push({ title: 'Document updated', variant: 'success' })
      }

      // Reload list so table reflects latest server state
      await loadDocs()
    } catch (err) {
      if (!options?.silent) {
        toast.push({
          title: 'Save failed',
          description: err instanceof ApiError && err.status === 403 ? "You don't have access" : 'Please try again.',
          variant: 'error',
        })
      }
    } finally {
      setSavingDocId(null)
    }
  }

  const scheduleAutoSave = (doc: DocumentItem) => {
    if (!canWrite || doc.processing_status !== 'done') return
    if (autoSaveInFlight.current[doc.id]) return

    if (autoSaveTimers.current[doc.id]) {
      window.clearTimeout(autoSaveTimers.current[doc.id])
    }

    autoSaveTimers.current[doc.id] = window.setTimeout(async () => {
      autoSaveInFlight.current[doc.id] = true
      await saveEdits(doc, { silent: true })
      autoSaveInFlight.current[doc.id] = false
      delete autoSaveTimers.current[doc.id]
    }, 900)
  }

  const upload = async () => {
    if (!file) return
    const form = new FormData()
    form.append('file', file)
    setUploading(true)
    try {
      await apiFetch('/documents/upload', { method: 'POST', body: form })
      toast.push({ title: 'Upload received', description: 'Document is processing.', variant: 'success' })
      setFile(null)
      await loadDocs()
    } catch (err) {
      toast.push({
        title: 'Upload failed',
        description: err instanceof ApiError && err.status === 403 ? "You don't have access" : 'Please try again.',
        variant: 'error',
      })
    } finally {
      setUploading(false)
    }
  }

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setIsDragging(false)
    const dropped = event.dataTransfer.files?.[0]
    if (dropped) setFile(dropped)
  }

  const selectedDoc = useMemo(() => documents.find((d) => d.id === expanded) ?? null, [documents, expanded])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700 shadow-sm">
            <span className="h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.75)]" />
            Docs Pipeline
          </div>
          <h1 className="mt-3 text-2xl font-semibold text-slate-900">Documents</h1>
          <p className="mt-1 text-sm text-slate-500">Upload, review extraction, and correct fields.</p>
        </div>
        <Badge variant={uploading ? 'warning' : 'info'}>{uploading ? 'Processing upload' : 'Ready'}</Badge>
      </div>

      {/* Upload */}
      <Card>
        <CardHeader>
          <CardTitle>Upload new document</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            className={cx(
              'flex flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-8 text-center text-sm transition',
              isDragging ? 'border-cyan-400 bg-cyan-50/30' : 'border-slate-200 bg-white'
            )}
            onDragOver={(event) => {
              event.preventDefault()
              setIsDragging(true)
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
          >
            <div className="text-2xl">📄</div>
            <div className="mt-2 font-semibold text-slate-800">Drag & drop files here</div>
            <div className="mt-1 text-xs text-slate-500">PDF, DOCX, or image files are accepted.</div>

            <input
              type="file"
              className="mt-4 text-xs"
              disabled={!canWrite}
              onChange={(event) => setFile(event.target.files?.[0] || null)}
            />

            <Button className="mt-4" onClick={upload} disabled={!canWrite || !file || uploading}>
              {uploading ? 'Uploading…' : file ? `Upload ${file.name}` : 'Select file'}
            </Button>

            {!canWrite ? (
              <div className="mt-3 text-xs text-slate-400">You don’t have permission to upload documents.</div>
            ) : null}
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card className="overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Filename</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>

          <TableBody>
            {documents.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-sm text-slate-500">
                  No documents uploaded yet.
                </TableCell>
              </TableRow>
            ) : null}

            {documents.map((doc) => (
              <Fragment key={doc.id}>
                <TableRow className={expanded === doc.id ? 'bg-slate-50' : ''}>
                  <TableCell className="font-medium">{doc?.filename ?? 'Not Available'}</TableCell>

                  <TableCell>
                    <Badge variant="default">{doc?.document_type ?? 'pending'}</Badge>
                  </TableCell>

                  <TableCell>
                    <Badge variant={statusVariant(doc.processing_status)}>
                      {doc?.processing_status === 'processing' ? 'Processing…' : doc?.processing_status ?? 'unknown'}
                    </Badge>
                    {doc.needs_review ? (
                      <Badge className="ml-2" variant="danger">
                        Needs review
                      </Badge>
                    ) : null}
                  </TableCell>

                  <TableCell>{doc?.created_at ? new Date(doc.created_at).toLocaleString() : 'Not Available'}</TableCell>

                  <TableCell className="space-x-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        const nextExpanded = expanded === doc.id ? null : doc.id
                        setExpanded(nextExpanded)
                        if (nextExpanded) ensureEditValues(doc)
                      }}
                    >
                      {expanded === doc.id ? 'Close' : 'Details'}
                    </Button>

                    {canWrite ? (
                      <Button
                        size="sm"
                        onClick={async () => {
                          await reprocessDocument(doc.id)
                          toast.push({ title: 'Reprocess queued', variant: 'info' })
                          await loadDocs()
                        }}
                      >
                        Reprocess
                      </Button>
                    ) : null}

                    {doc.processing_status === 'done' ? (
                      <Link className="text-xs font-semibold text-slate-600 hover:underline" to="/proposals">
                        Related proposals
                      </Link>
                    ) : null}

                    <a
                      className="text-xs font-semibold text-slate-600 hover:underline"
                      href={buildApiUrl(`/documents/${doc.id}/download`)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Preview
                    </a>

                    {canWrite && doc.processing_status === 'queued' ? (
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={async () => {
                          if (!confirm('Delete this queued document?')) return
                          await apiFetch(`/documents/${doc.id}`, { method: 'DELETE' })
                          toast.push({ title: 'Document deleted', variant: 'info' })
                          await loadDocs()
                        }}
                      >
                        Delete
                      </Button>
                    ) : null}
                  </TableCell>
                </TableRow>

                {/* Expanded detail */}
                {expanded === doc.id ? (
                  <TableRow className="bg-slate-50">
                    <TableCell colSpan={5}>
                      <div className="grid gap-4 lg:grid-cols-2">
                        {/* Summary */}
                        <Card className="p-4">
                          <CardTitle>Agent summary</CardTitle>
                          <textarea
                            className="mt-3 w-full rounded-2xl border border-slate-200 bg-white p-3 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-cyan-300/40"
                            rows={7}
                            value={editValues[doc.id]?.agent_summary ?? ''}
                            onChange={(event) => {
                              updateEditField(doc.id, 'agent_summary', event.target.value)
                              scheduleAutoSave(doc)
                            }}
                            disabled={!canWrite}
                          />
                        </Card>

                        {/* JSON */}
                        <Card className="p-4">
                          <div className="flex items-center justify-between gap-2">
                            <CardTitle>Extracted fields (JSON)</CardTitle>
                            <button
                              type="button"
                              className="text-xs font-semibold text-slate-600 hover:underline"
                              onClick={() => validateJson(doc.id)}
                            >
                              Validate
                            </button>
                          </div>

                          <textarea
                            className={cx(
                              'mt-3 h-56 w-full rounded-2xl border bg-white p-3 font-mono text-xs shadow-sm',
                              'focus:outline-none focus:ring-2 focus:ring-cyan-300/40',
                              jsonErrors[doc.id] ? 'border-rose-300' : 'border-slate-200'
                            )}
                            value={editValues[doc.id]?.extracted_fields ?? '{}'}
                            onChange={(event) => {
                              updateEditField(doc.id, 'extracted_fields', event.target.value)
                              scheduleAutoSave(doc)
                            }}
                            onBlur={() => validateJson(doc.id)}
                            disabled={!canWrite}
                          />

                          {jsonErrors[doc.id] ? (
                            <div className="mt-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
                              {jsonErrors[doc.id]}
                            </div>
                          ) : (
                            <div className="mt-2 text-xs text-slate-500">
                              Tip: keep valid JSON. Use Validate if unsure.
                            </div>
                          )}

                          {getLowConfidenceFields(doc?.extracted_fields).length > 0 ? (
                            <div className="mt-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
                              Low confidence fields: {getLowConfidenceFields(doc?.extracted_fields).join(', ')}
                            </div>
                          ) : null}
                        </Card>

                        {/* Metadata */}
                        <Card className="p-4">
                          <CardTitle>Document metadata</CardTitle>

                          <label className="mt-3 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                            Document type
                          </label>

                          <select
                            className="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-cyan-300/40"
                            value={editValues[doc.id]?.document_type ?? ''}
                            onChange={(event) => {
                              updateEditField(doc.id, 'document_type', event.target.value)
                              scheduleAutoSave(doc)
                            }}
                            disabled={!canWrite}
                          >
                            <option value="">(unset)</option>
                            {DOCUMENT_TYPE_OPTIONS.map((t) => (
                              <option key={t} value={t}>
                                {t}
                              </option>
                            ))}
                          </select>

                          <div className="mt-3 text-xs text-slate-500">
                            Linked project: <span className="font-semibold text-slate-700">{doc.project_name ?? 'Unlinked'}</span>{' '}
                            • Linked customer:{' '}
                            <span className="font-semibold text-slate-700">{doc.customer_name ?? 'Unlinked'}</span>
                          </div>

                          <label className="mt-4 flex items-center gap-2 text-sm text-slate-700">
                            <input
                              type="checkbox"
                              checked={editValues[doc.id]?.needs_review ?? false}
                              onChange={(event) => {
                                updateEditField(doc.id, 'needs_review', event.target.checked)
                                scheduleAutoSave(doc)
                              }}
                              disabled={!canWrite}
                            />
                            Needs review
                          </label>

                          {doc.processing_error ? (
                            <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700">
                              {doc.processing_error}
                            </div>
                          ) : null}
                        </Card>

                        {/* Actions */}
                        <Card className="p-4">
                          <CardTitle>Actions</CardTitle>
                          <p className="mt-2 text-sm text-slate-500">
                            Changes are auto-saved after AI processing. Use Save now if you want to force a sync.
                          </p>

                          <div className="mt-4 flex flex-wrap gap-2">
                            <Button
                              onClick={() => void saveEdits(doc)}
                              disabled={!canWrite || savingDocId === doc.id}
                            >
                              {savingDocId === doc.id ? 'Saving…' : 'Save now'}
                            </Button>

                            <Button
                              variant="secondary"
                              onClick={() => {
                                // Reset edits back to doc values
                                setEditValues((cur) => ({
                                  ...cur,
                                  [doc.id]: {
                                    document_type: doc.document_type ?? '',
                                    agent_summary: doc.agent_summary ?? '',
                                    extracted_fields: JSON.stringify(doc.extracted_fields ?? {}, null, 2),
                                    needs_review: doc.needs_review,
                                  },
                                }))
                                setJsonErrors((cur) => {
                                  const next = { ...cur }
                                  delete next[doc.id]
                                  return next
                                })
                              }}
                              disabled={savingDocId === doc.id}
                            >
                              Reset
                            </Button>
                          </div>

                          {!canWrite ? (
                            <div className="mt-3 text-xs text-slate-400">
                              You don’t have permission to edit documents.
                            </div>
                          ) : null}
                        </Card>

                        {/* Versions */}
                        <Card className="p-4">
                          <CardTitle>Versions</CardTitle>
                          {doc.versions && doc.versions.length > 0 ? (
                            <ul className="mt-2 space-y-1 text-xs text-slate-600">
                              {doc.versions.map((version) => (
                                <li key={version.id}>
                                  <span className="font-semibold text-slate-800">v{version.version}</span> •{' '}
                                  {new Date(version.created_at).toLocaleString()}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <div className="mt-2 text-xs text-slate-400">No versions yet.</div>
                          )}
                        </Card>

                        {/* Linked proposals */}
                        <Card className="p-4">
                          <CardTitle>Linked proposals</CardTitle>
                          {doc.proposals && doc.proposals.length > 0 ? (
                            <ul className="mt-2 space-y-2 text-xs text-slate-700">
                              {doc.proposals.map((proposal) => (
                                <li key={proposal.id} className="rounded-xl border border-slate-200 bg-white p-2">
                                  <div className="font-semibold text-slate-800">
                                    {proposal.target_table} • {proposal.status}
                                  </div>
                                  <div className="mt-1 text-slate-600">{proposal.proposed_action}</div>
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <div className="mt-2 text-xs text-slate-400">No linked proposals.</div>
                          )}
                        </Card>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : null}
              </Fragment>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
