import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { apiFetch } from '../api'
import { useToast } from '../components/Toast'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import { Card, CardContent, CardHeader } from '../components/ui/Card'

interface ProposalItem {
  id: number
  doc_version_id: number
  target_table: string
  target_module: string
  proposed_action: string
  proposed_fields: Record<string, unknown>
  field_confidence: Record<string, number>
  evidence: Record<string, { snippet?: string; location?: string; source?: string }>
  questions: Record<string, unknown>
  status: string
  created_at: string
}

interface ChatSession {
  id: number
  title?: string | null
  created_at: string
  updated_at: string
}

interface ChatMessage {
  id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
}

interface UserMemory {
  id: number
  type: string
  key?: string | null
  content: string
  relevance: number
  created_at: string
  updated_at: string
}

const iconMap: Record<string, string> = {
  tasks: '✅',
  projects: '📌',
  issues: '🚩',
  ncrs: '🛠️',
  customers: '🏢',
}

function cx(...classes: Array<string | false | undefined | null>) {
  return classes.filter(Boolean).join(' ')
}

const summarizeFields = (fields: Record<string, unknown>) => {
  const entries = Object.entries(fields || {})
  if (entries.length === 0) return 'No extracted fields yet.'
  return entries
    .slice(0, 4)
    .map(([key, value]) => {
      const display = typeof value === 'object' ? JSON.stringify(value) : String(value)
      return `${key}: ${display.slice(0, 26)}`
    })
    .join(' · ')
}

const averageConfidence = (fieldConfidence: Record<string, number>) => {
  const values = Object.values(fieldConfidence || {})
  if (!values.length) return 0
  const total = values.reduce((sum, value) => sum + (typeof value === 'number' ? value : 0), 0)
  return total / values.length
}

const extractEvidenceSnippet = (evidence: Record<string, { snippet?: string; location?: string; source?: string }>) => {
  const entries = Object.values(evidence || {})
  const snippet = entries.find((entry) => entry?.snippet)?.snippet
  return snippet ? snippet.slice(0, 180) : ''
}

const hasOpenQuestions = (questions: Record<string, unknown>) => {
  return Object.values(questions || {}).some((value) => {
    if (!value) return false
    if (Array.isArray(value)) return value.length > 0
    if (typeof value === 'string') return value.trim().length > 0
    return true
  })
}

function confidenceVariant(conf: number) {
  if (conf >= 0.9) return 'success'
  if (conf >= 0.75) return 'warning'
  return 'danger'
}

export default function InboxPage() {
  const [items, setItems] = useState<ProposalItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [sessionId, setSessionId] = useState<number | null>(null)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)

  const [memoryOpen, setMemoryOpen] = useState(false)
  const [memories, setMemories] = useState<UserMemory[]>([])
  const [memoryLoading, setMemoryLoading] = useState(false)

  const [selectedProposalId, setSelectedProposalId] = useState<number | null>(null)

  const navigate = useNavigate()
  const toast = useToast()

  // Scroll refs
  const chatScrollRef = useRef<HTMLDivElement | null>(null)
  const chatBottomRef = useRef<HTMLDivElement | null>(null)

  const scrollChatToBottom = (smooth = true) => {
    const el = chatBottomRef.current
    if (!el) return
    el.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'end' })
  }

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const data = (await apiFetch('/proposals?status=pending')) as ProposalItem[]
      setItems(data)
      setSelectedProposalId((prev) => prev ?? data[0]?.id ?? null)
    } catch {
      setError('Unable to load AI actions. Please retry.')
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  const loadOrCreateSession = async () => {
    try {
      const sessions = (await apiFetch('/ai/sessions')) as ChatSession[]
      const activeSession =
        sessions[0] ??
        ((await apiFetch('/ai/sessions', {
          method: 'POST',
          body: JSON.stringify({ title: 'AI Inbox' }),
        })) as ChatSession)

      setSessionId(activeSession.id)
      const msgs = (await apiFetch(`/ai/sessions/${activeSession.id}/messages`)) as ChatMessage[]
      setChatMessages(msgs)

      // After initial load, jump to bottom
      setTimeout(() => scrollChatToBottom(false), 0)
    } catch {
      toast.push({ title: 'AI unavailable', description: 'Could not initialize AI chat session.', variant: 'error' })
    }
  }

  useEffect(() => {
    void load()
    void loadOrCreateSession()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Auto-scroll when messages change
  useEffect(() => {
    // don’t yank scroll if user is reading older messages
    const container = chatScrollRef.current
    if (!container) return
    const nearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 120
    if (nearBottom) scrollChatToBottom(true)
  }, [chatMessages.length])

  const quickApprove = async (proposal: ProposalItem) => {
    try {
      setItems((current) => current.filter((item) => item.id !== proposal.id))
      await apiFetch(`/proposals/${proposal.id}/approve`, {
        method: 'POST',
        body: JSON.stringify({ proposed_fields: proposal.proposed_fields }),
      })
      toast.push({
        title: 'AI action approved',
        description: `Proposal #${proposal.id} has been approved.`,
        variant: 'success',
      })
    } catch {
      toast.push({
        title: 'Approval failed',
        description: 'Please review the proposal before approving.',
        variant: 'error',
      })
      void load()
    }
  }

  const sendMessage = async (event: FormEvent) => {
    event.preventDefault()
    const message = chatInput.trim()
    if (!message || chatLoading || !sessionId) return

    const optimisticMessage: ChatMessage = {
      id: Date.now(),
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    }
    setChatMessages((current) => [...current, optimisticMessage])
    setChatInput('')
    setChatLoading(true)

    try {
      const response = (await apiFetch(`/ai/sessions/${sessionId}/messages`, {
        method: 'POST',
        body: JSON.stringify({
          message,
          context: {
            page: 'inbox',
            pending_proposals: items.length,
            selected_proposal_id: selectedProposalId,
          },
        }),
      })) as { reply: string }

      setChatMessages((current) => [
        ...current,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: response.reply,
          created_at: new Date().toISOString(),
        },
      ])
    } catch {
      toast.push({ title: 'AI chat failed', description: 'Could not reach AI assistant. Please try again.', variant: 'error' })
    } finally {
      setChatLoading(false)
    }
  }

  const openMemory = async () => {
    setMemoryOpen(true)
    setMemoryLoading(true)
    try {
      const data = (await apiFetch('/ai/memory')) as UserMemory[]
      setMemories(data)
    } catch {
      toast.push({ title: 'Memory load failed', description: 'Could not load saved AI memory.', variant: 'error' })
    } finally {
      setMemoryLoading(false)
    }
  }

  const deleteMemory = async (memoryId: number) => {
    try {
      await apiFetch(`/ai/memory/${memoryId}`, { method: 'DELETE' })
      setMemories((current) => current.filter((memory) => memory.id !== memoryId))
    } catch {
      toast.push({ title: 'Delete failed', description: 'Could not delete this memory item.', variant: 'error' })
    }
  }

  const pendingCount = items.length
  const groupedItems = useMemo(
    () =>
      items.reduce<Record<string, ProposalItem[]>>((groups, proposal) => {
        const dateKey = new Date(proposal.created_at).toLocaleDateString()
        const groupKey = `${proposal.doc_version_id}|${dateKey}`
        if (!groups[groupKey]) groups[groupKey] = []
        groups[groupKey].push(proposal)
        return groups
      }, {}),
    [items],
  )

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {/* Hide scrollbar but keep scroll (no CSS file needed) */}
      <style>
        {`
          .no-scrollbar::-webkit-scrollbar { display: none; }
          .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
        `}
      </style>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700 shadow-sm">
            <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.8)]" />
            AI Review Queue
          </div>

          <h1 className="mt-3 text-3xl font-semibold text-slate-900">AI Inbox</h1>
          <p className="mt-1 text-sm text-slate-500">
            Review pending AI actions and coordinate next steps with chat.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant={pendingCount > 0 ? 'warning' : 'success'}>{pendingCount} pending</Badge>
          <Button variant="secondary" onClick={() => void load()}>
            Refresh
          </Button>
        </div>
      </div>

      {/* Layout */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Pending actions */}
        <Card className="lg:col-span-7">
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">Pending actions</h2>
                <p className="mt-1 text-sm text-slate-500">Grouped by document version and date.</p>
              </div>

              <div className="text-xs text-slate-500">
                Tip: click a card to “select” it for AI chat context.
              </div>
            </div>
          </CardHeader>

          <CardContent>
            {loading ? (
              <div className="space-y-4">
                {[...Array(4)].map((_, index) => (
                  <div key={index} className="space-y-3 rounded-2xl border border-slate-200 p-4">
                    <div className="h-3 w-48 animate-pulse rounded bg-slate-200" />
                    <div className="h-3 w-full animate-pulse rounded bg-slate-100" />
                    <div className="h-3 w-4/5 animate-pulse rounded bg-slate-100" />
                    <div className="h-8 w-56 animate-pulse rounded bg-slate-100" />
                  </div>
                ))}
              </div>
            ) : null}

            {error ? (
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-8 text-center">
                <p className="text-sm text-slate-600">{error}</p>
                <Button className="mt-4" variant="secondary" onClick={() => void load()}>
                  Retry
                </Button>
              </div>
            ) : null}

            {!loading && !error && items.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-10 text-center text-sm text-slate-500">
                <p>No pending AI actions right now.</p>
                <p className="mt-2">Check back soon or refresh to look for new suggestions.</p>
                <Button className="mt-4" variant="secondary" onClick={() => void load()}>
                  Retry
                </Button>
              </div>
            ) : null}

            {!loading && !error && items.length > 0 ? (
              <div className="space-y-4 lg:max-h-[72vh] lg:overflow-auto lg:pr-2">
                {Object.entries(groupedItems).map(([groupKey, proposals]) => {
                  const [docVersionId, dateKey] = groupKey.split('|')
                  return (
                    <div key={groupKey} className="space-y-3 rounded-2xl border border-slate-200 bg-slate-50/60 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
                        <span className="font-medium text-slate-600">Document version #{docVersionId}</span>
                        <span>{dateKey}</span>
                      </div>

                      <div className="space-y-3">
                        {proposals.map((proposal) => {
                          const confidence = averageConfidence(proposal.field_confidence)
                          const quickApproveAllowed = confidence >= 0.86 && !hasOpenQuestions(proposal.questions)
                          const questionsOpen = hasOpenQuestions(proposal.questions)
                          const selected = selectedProposalId === proposal.id

                          return (
                            <button
                              key={proposal.id}
                              type="button"
                              onClick={() => setSelectedProposalId(proposal.id)}
                              className={cx(
                                'group relative w-full overflow-hidden rounded-2xl border bg-white p-4 text-left',
                                'transition duration-200 active:scale-[0.99]',
                                selected ? 'border-emerald-300/60' : 'border-slate-200 hover:border-slate-300'
                              )}
                            >
                              {selected ? (
                                <>
                                  <span
                                    className={cx(
                                      'absolute inset-0 rounded-2xl',
                                      'bg-gradient-to-r from-emerald-500/15 via-cyan-400/18 to-fuchsia-500/15',
                                      'shadow-[0_0_18px_rgba(16,185,129,0.30)]'
                                    )}
                                    aria-hidden="true"
                                  />
                                  <span
                                    className={cx(
                                      'absolute -inset-1 rounded-3xl blur-xl',
                                      'bg-gradient-to-r from-emerald-400/12 via-cyan-400/12 to-fuchsia-400/12',
                                      'animate-pulse'
                                    )}
                                    aria-hidden="true"
                                  />
                                  <span className="absolute inset-0 overflow-hidden rounded-2xl" aria-hidden="true">
                                    <span
                                      className={cx(
                                        'absolute inset-0',
                                        'bg-[linear-gradient(120deg,transparent_0%,rgba(255,255,255,0.14)_45%,transparent_60%)]',
                                        'translate-x-[-120%] group-hover:translate-x-[120%]',
                                        'transition-transform duration-700 ease-out'
                                      )}
                                    />
                                  </span>
                                  <span
                                    className={cx(
                                      'absolute left-2 top-1/2 h-10 w-1 -translate-y-1/2 rounded-full',
                                      'bg-gradient-to-b from-emerald-300 via-cyan-300 to-fuchsia-300',
                                      'shadow-[0_0_12px_rgba(34,211,238,0.65)]'
                                    )}
                                    aria-hidden="true"
                                  />
                                </>
                              ) : null}

                              <div className="relative space-y-3">
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <div className="text-sm font-semibold text-slate-800">
                                    {iconMap[proposal.target_table] ?? '🤖'} {proposal.target_table} · #{proposal.id}
                                  </div>

                                  <div className="flex items-center gap-2">
                                    {questionsOpen ? (
                                      <span className="rounded-full bg-amber-50 px-2 py-1 text-[11px] font-semibold text-amber-700 ring-1 ring-amber-200">
                                        Questions
                                      </span>
                                    ) : (
                                      <span className="rounded-full bg-emerald-50 px-2 py-1 text-[11px] font-semibold text-emerald-700 ring-1 ring-emerald-200">
                                        Clear
                                      </span>
                                    )}

                                    <Badge variant={confidenceVariant(confidence)}>
                                      {(confidence * 100).toFixed(0)}% confidence
                                    </Badge>
                                  </div>
                                </div>

                                <p className="text-sm leading-relaxed text-slate-600">{summarizeFields(proposal.proposed_fields)}</p>

                                {extractEvidenceSnippet(proposal.evidence) ? (
                                  <p className="rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-500 ring-1 ring-slate-900/5">
                                    <span className="font-semibold text-slate-600">Evidence:</span> “{extractEvidenceSnippet(proposal.evidence)}”
                                  </p>
                                ) : null}

                                <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                                  <span className="rounded-full bg-slate-100 px-2 py-1">Target: {proposal.target_table}</span>
                                  <span className="rounded-full bg-slate-100 px-2 py-1">{new Date(proposal.created_at).toLocaleString()}</span>
                                  {selected ? (
                                    <span className="rounded-full bg-emerald-50 px-2 py-1 font-semibold text-emerald-700 ring-1 ring-emerald-200">
                                      Selected for chat
                                    </span>
                                  ) : null}
                                </div>

                                <div className="flex flex-wrap gap-2 pt-1">
                                  <Button variant="secondary" onClick={() => navigate(`/proposals/${proposal.id}`)}>
                                    Review
                                  </Button>
                                  <Button onClick={() => navigate(`/proposals/${proposal.id}`)}>Approve</Button>
                                  {quickApproveAllowed ? (
                                    <Button variant="ghost" onClick={() => void quickApprove(proposal)}>
                                      Quick Approve
                                    </Button>
                                  ) : null}
                                  <Button variant="destructive" onClick={() => navigate(`/proposals/${proposal.id}`)}>
                                    Reject
                                  </Button>
                                </div>
                              </div>
                            </button>
                          )
                        })}
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : null}
          </CardContent>
        </Card>

        {/* AI Chat */}
        <div className="lg:sticky lg:top-6 lg:col-span-5">
          <Card className="flex h-[70vh] flex-col overflow-hidden">
            <CardHeader className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">AI Chat</h2>
                <p className="mt-1 text-sm text-slate-500">Ask for summaries, risk checks, or next best action.</p>
                {selectedProposalId ? (
                  <div className="mt-2 text-xs text-slate-500">
                    Context: <span className="font-semibold text-slate-700">Proposal #{selectedProposalId}</span>
                  </div>
                ) : null}
              </div>

              <Button variant="secondary" size="sm" onClick={() => void openMemory()}>
                Memory
              </Button>
            </CardHeader>

            {/* IMPORTANT: min-h-0 makes scroll work inside flex layouts */}
            <CardContent className="flex min-h-0 flex-1 flex-col gap-3">
              <div
                ref={chatScrollRef}
                className="no-scrollbar min-h-0 flex-1 space-y-3 overflow-y-auto rounded-2xl bg-slate-50 p-3 ring-1 ring-slate-900/5"
              >
                {chatMessages.length === 0 ? (
                  <p className="text-sm text-slate-500">
                    Ask AI: “Summarize top risks”, “Which proposal is safest to approve?”, “Draft corrective action…”
                  </p>
                ) : (
                  chatMessages
                    .filter((m) => m.role !== 'system')
                    .map((message) => {
                      const isUser = message.role === 'user'
                      return (
                        <div key={message.id} className={cx('flex', isUser ? 'justify-end' : 'justify-start')}>
                          <div
                            className={cx(
                              'relative max-w-[92%] rounded-2xl px-3 py-2 text-sm leading-relaxed',
                              isUser ? 'bg-slate-900 text-white' : 'bg-white text-slate-700 ring-1 ring-slate-900/5',
                              !isUser ? 'shadow-[0_0_18px_rgba(34,211,238,0.08)]' : ''
                            )}
                          >
                            {!isUser ? (
                              <span
                                className="pointer-events-none absolute -inset-1 rounded-3xl bg-gradient-to-r from-emerald-400/0 via-cyan-400/12 to-fuchsia-400/0 blur-xl"
                                aria-hidden="true"
                              />
                            ) : null}
                            <span className="relative">{message.content}</span>
                          </div>
                        </div>
                      )
                    })
                )}

                {chatLoading ? <p className="text-sm text-slate-500">Thinking…</p> : null}

                {/* bottom anchor for auto-scroll */}
                <div ref={chatBottomRef} />
              </div>

              <form className="flex gap-2" onSubmit={sendMessage}>
                <input
                  className={cx(
                    'flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm',
                    'shadow-sm ring-1 ring-slate-900/5',
                    'focus:outline-none focus:ring-2 focus:ring-emerald-400/40'
                  )}
                  value={chatInput}
                  onChange={(event) => setChatInput(event.target.value)}
                  placeholder="Ask AI about these proposals..."
                  disabled={chatLoading}
                />
                <Button type="submit" disabled={chatLoading || !chatInput.trim() || !sessionId}>
                  Send
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Memory modal */}
      {memoryOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
          onClick={() => setMemoryOpen(false)}
        >
          <Card
            className="relative max-h-[78vh] w-full max-w-2xl overflow-hidden"
            onClick={(event) => event.stopPropagation()}
          >
            <span
              className="pointer-events-none absolute -inset-1 rounded-3xl bg-gradient-to-r from-emerald-400/10 via-cyan-400/12 to-fuchsia-400/10 blur-xl"
              aria-hidden="true"
            />

            <CardHeader className="relative flex items-start justify-between gap-4">
              <div>
                <h3 className="text-lg font-semibold text-slate-900">Your AI Memory</h3>
                <p className="mt-1 text-sm text-slate-500">Saved context used to personalize replies.</p>
              </div>
              <Button variant="secondary" size="sm" onClick={() => setMemoryOpen(false)}>
                Close
              </Button>
            </CardHeader>

            <CardContent className="relative">
              <div className="no-scrollbar max-h-[65vh] space-y-3 overflow-auto pr-1">
                {memoryLoading ? <p className="text-sm text-slate-500">Loading memory…</p> : null}
                {!memoryLoading && memories.length === 0 ? <p className="text-sm text-slate-500">No memory items yet.</p> : null}

                {!memoryLoading
                  ? memories.map((memory) => (
                      <div
                        key={memory.id}
                        className="flex items-start justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm ring-1 ring-slate-900/5"
                      >
                        <div className="min-w-0">
                          <p className="text-xs uppercase tracking-wide text-slate-500">{memory.type}</p>
                          <p className="mt-1 text-sm text-slate-700">{memory.content}</p>
                          <p className="mt-1 text-xs text-slate-400">Relevance: {(memory.relevance * 100).toFixed(0)}%</p>
                        </div>
                        <Button variant="destructive" size="sm" onClick={() => void deleteMemory(memory.id)}>
                          Delete
                        </Button>
                      </div>
                    ))
                  : null}
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </div>
  )
}
