import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'

import { apiFetch } from '../api'
import { useAuth } from '../auth/AuthContext'
import Button from '../components/ui/Button'
import { Card, CardContent, CardHeader } from '../components/ui/Card'
import Input from '../components/ui/Input'

type ChatMode = 'direct' | 'global'

interface MessageUser {
  id: number
  name: string
  email: string
}

interface ChatMessage {
  id: number
  room_id: number
  sender_user_id: number
  content: string
  created_at: string
  sender: MessageUser
}

interface MessageRoom {
  id: number
  type: 'dm' | 'global'
  created_at: string
}

type DirectPreview = {
  roomId: number
  latestId: number
  latestAt: number // epoch ms
  latestText: string
  hasUnseen: boolean
}

const LS_LAST_SEEN_KEY = 'messages:lastSeenDirectByUser:v1'

function normalize(s: string) {
  return s.trim().toLowerCase()
}

export default function MessagesPage() {
  const { user } = useAuth()

  const [mode, setMode] = useState<ChatMode>('global')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [users, setUsers] = useState<MessageUser[]>([])
  const [selectedUser, setSelectedUser] = useState<MessageUser | null>(null)

  const [globalRoomId, setGlobalRoomId] = useState<number | null>(null)
  const [directRoomId, setDirectRoomId] = useState<number | null>(null)

  const [globalMessages, setGlobalMessages] = useState<ChatMessage[]>([])
  const [directMessages, setDirectMessages] = useState<ChatMessage[]>([])
  const [globalInput, setGlobalInput] = useState('')
  const [directInput, setDirectInput] = useState('')
  const [sending, setSending] = useState(false)

  const [globalLoading, setGlobalLoading] = useState(false)
  const [directLoading, setDirectLoading] = useState(false)

  const [globalError, setGlobalError] = useState('')
  const [directError, setDirectError] = useState('')

  // Global unseen dot
  const [hasUnseenGlobal, setHasUnseenGlobal] = useState(false)
  const lastSeenGlobalIdRef = useRef<number>(0)
  const lastGlobalLatestIdRef = useRef<number>(0)

  // Per-user direct previews (sorting + unseen glow)
  const [directPreviews, setDirectPreviews] = useState<Record<number, DirectPreview>>({})
  const lastSeenDirectByUserRef = useRef<Record<number, number>>({})
  const selectedUserIdRef = useRef<number | null>(null)

  // ✅ Realtime “streaming” search state (client-side, instant filtering)
  const [userSearch, setUserSearch] = useState('')
  const userSearchInputRef = useRef<HTMLInputElement | null>(null)

  const persistLastSeen = (next: Record<number, number>) => {
    lastSeenDirectByUserRef.current = next
    try {
      window.localStorage.setItem(LS_LAST_SEEN_KEY, JSON.stringify(next))
    } catch {
      // ignore
    }
  }

  const loadLastSeenFromStorage = () => {
    try {
      const raw = window.localStorage.getItem(LS_LAST_SEEN_KEY)
      if (!raw) return
      const parsed = JSON.parse(raw) as Record<number, number>
      if (parsed && typeof parsed === 'object') lastSeenDirectByUserRef.current = parsed
    } catch {
      // ignore
    }
  }

  const loadInitial = async () => {
    setLoading(true)
    setError('')
    try {
      loadLastSeenFromStorage()

      const [globalRoom, usersData] = await Promise.all([
        apiFetch('/messages/global') as Promise<MessageRoom>,
        apiFetch('/messages/users') as Promise<MessageUser[]>,
      ])
      setGlobalRoomId(globalRoom.id)
      setUsers(usersData)
      if (usersData.length > 0) {
        setSelectedUser(usersData[0])
      }
    } catch {
      setError('Unable to load messages. Please refresh.')
    } finally {
      setLoading(false)
    }
  }

  const loadMessages = async (roomId: number, target: ChatMode) => {
    if (target === 'global') {
      setGlobalLoading(true)
      setGlobalError('')
    } else {
      setDirectLoading(true)
      setDirectError('')
    }

    try {
      const data = (await apiFetch(`/messages/rooms/${roomId}`)) as ChatMessage[]
      if (target === 'global') setGlobalMessages(data)
      else setDirectMessages(data)
    } catch {
      if (target === 'global') setGlobalError('Failed to load global messages.')
      else setDirectError('Failed to load direct messages.')
    } finally {
      if (target === 'global') setGlobalLoading(false)
      else setDirectLoading(false)
    }
  }

  const openDmRoom = async (peer: MessageUser) => {
    setDirectLoading(true)
    setDirectError('')
    try {
      const room = (await apiFetch(`/messages/dm/${peer.id}`, { method: 'POST' })) as MessageRoom
      setDirectRoomId(room.id)
      await loadMessages(room.id, 'direct')
    } catch {
      setDirectError('Failed to open direct chat room.')
      setDirectLoading(false)
    }
  }

  const refreshDirectPreviewForUser = async (peer: MessageUser) => {
    try {
      const room = (await apiFetch(`/messages/dm/${peer.id}`, { method: 'POST' })) as MessageRoom
      const msgs = (await apiFetch(`/messages/rooms/${room.id}`)) as ChatMessage[]

      const latest = msgs[msgs.length - 1]
      const latestId = latest?.id ?? 0
      const latestAt = latest ? new Date(latest.created_at).getTime() : 0
      const latestText = latest?.content ?? ''

      const lastSeen = lastSeenDirectByUserRef.current[peer.id] ?? 0
      const hasUnseen = latestId > lastSeen && peer.id !== selectedUserIdRef.current

      setDirectPreviews((prev) => ({
        ...prev,
        [peer.id]: {
          roomId: room.id,
          latestId,
          latestAt,
          latestText,
          hasUnseen,
        },
      }))
    } catch {
      // ignore preview failures
    }
  }

  const refreshAllDirectPreviews = async (peers: MessageUser[]) => {
    for (const peer of peers) {
      // eslint-disable-next-line no-await-in-loop
      await refreshDirectPreviewForUser(peer)
    }
  }

  useEffect(() => {
    void loadInitial()
  }, [])

  useEffect(() => {
    if (!globalRoomId) return
    void loadMessages(globalRoomId, 'global')
  }, [globalRoomId])

  useEffect(() => {
    selectedUserIdRef.current = selectedUser?.id ?? null
  }, [selectedUser?.id])

  useEffect(() => {
    if (!selectedUser) {
      setDirectRoomId(null)
      setDirectMessages([])
      return
    }

    void (async () => {
      await openDmRoom(selectedUser)

      const preview = directPreviews[selectedUser.id]
      const latestId = preview?.latestId ?? 0

      const next = {
        ...lastSeenDirectByUserRef.current,
        [selectedUser.id]: Math.max(lastSeenDirectByUserRef.current[selectedUser.id] ?? 0, latestId),
      }
      persistLastSeen(next)

      setDirectPreviews((prev) => ({
        ...prev,
        [selectedUser.id]: prev[selectedUser.id] ? { ...prev[selectedUser.id], hasUnseen: false } : prev[selectedUser.id],
      }))

      await refreshDirectPreviewForUser(selectedUser)
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedUser?.id])

  useEffect(() => {
    if (users.length === 0) return
    void refreshAllDirectPreviews(users)

    const id = window.setInterval(() => void refreshAllDirectPreviews(users), 8000)
    return () => window.clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [users.map((u) => u.id).join(',')])

  useEffect(() => {
    if (!globalRoomId) return
    const tick = async () => {
      await loadMessages(globalRoomId, 'global')
    }
    void tick()
    const id = window.setInterval(() => void tick(), 5000)
    return () => window.clearInterval(id)
  }, [globalRoomId])

  useEffect(() => {
    if (!directRoomId) return
    const tick = async () => {
      await loadMessages(directRoomId, 'direct')
    }
    void tick()
    const id = window.setInterval(() => void tick(), 5000)
    return () => window.clearInterval(id)
  }, [directRoomId])

  useEffect(() => {
    const latest = globalMessages[globalMessages.length - 1]?.id ?? 0
    if (!latest) return

    if (latest > lastGlobalLatestIdRef.current) {
      lastGlobalLatestIdRef.current = latest
      if (mode !== 'global') setHasUnseenGlobal(latest > lastSeenGlobalIdRef.current)
      else {
        lastSeenGlobalIdRef.current = latest
        setHasUnseenGlobal(false)
      }
    } else {
      if (mode === 'global') {
        lastSeenGlobalIdRef.current = latest
        setHasUnseenGlobal(false)
      } else {
        setHasUnseenGlobal(latest > lastSeenGlobalIdRef.current)
      }
    }
  }, [globalMessages, mode])

  useEffect(() => {
    if (!selectedUser) return
    const latest = directMessages[directMessages.length - 1]
    if (!latest) return

    const latestId = latest.id
    const latestAt = new Date(latest.created_at).getTime()

    setDirectPreviews((prev) => ({
      ...prev,
      [selectedUser.id]: {
        roomId: prev[selectedUser.id]?.roomId ?? (directRoomId ?? 0),
        latestId,
        latestAt,
        latestText: latest.content,
        hasUnseen: false,
      },
    }))

    const next = {
      ...lastSeenDirectByUserRef.current,
      [selectedUser.id]: Math.max(lastSeenDirectByUserRef.current[selectedUser.id] ?? 0, latestId),
    }
    persistLastSeen(next)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [directMessages])

  const sendMessage = async (event: FormEvent, target: ChatMode) => {
    event.preventDefault()
    const text = (target === 'global' ? globalInput : directInput).trim()
    const roomId = target === 'global' ? globalRoomId : directRoomId
    if (!text || !roomId || sending) return

    setSending(true)
    try {
      await apiFetch(`/messages/rooms/${roomId}`, {
        method: 'POST',
        body: JSON.stringify({ content: text }),
      })
      if (target === 'global') {
        setGlobalInput('')
        await loadMessages(roomId, 'global')
      } else {
        setDirectInput('')
        await loadMessages(roomId, 'direct')
      }
    } catch {
      if (target === 'global') setGlobalError('Failed to send global message.')
      else setDirectError('Failed to send direct message.')
    } finally {
      setSending(false)
    }
  }

  const renderMessages = (messages: ChatMessage[]) => (
    <div className="flex h-[28rem] flex-col overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="flex-1 overflow-y-auto bg-slate-50 p-4">
        {messages.length === 0 ? <p className="text-sm text-slate-500">No messages yet.</p> : null}
        <div className="space-y-3">
          {messages.map((message) => {
            const mine = message.sender_user_id === user?.id
            return (
              <div key={message.id} className={`flex ${mine ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] ${mine ? 'items-end' : 'items-start'}`}>
                  <div className={`mb-1 text-xs ${mine ? 'text-right text-slate-500' : 'text-slate-500'}`}>
                    {message.sender.name}
                  </div>

                  <div
                    className={[
                      'rounded-2xl px-4 py-2 text-sm shadow-sm',
                      mine ? 'bg-slate-900 text-white' : 'bg-white text-slate-700 ring-1 ring-slate-200',
                    ].join(' ')}
                  >
                    <div className="whitespace-pre-wrap leading-relaxed">{message.content}</div>
                  </div>

                  <div className={`mt-1 text-[11px] ${mine ? 'text-right text-slate-400' : 'text-slate-400'}`}>
                    {new Date(message.created_at).toLocaleString()}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )

  const directTitle = useMemo(() => {
    if (!selectedUser) return 'Select a user'
    return `Chat with ${selectedUser.name}`
  }, [selectedUser])

  const sortedUsers = useMemo(() => {
    const copy = [...users]
    copy.sort((a, b) => {
      const aAt = directPreviews[a.id]?.latestAt ?? 0
      const bAt = directPreviews[b.id]?.latestAt ?? 0
      if (bAt !== aAt) return bAt - aAt
      return a.name.localeCompare(b.name)
    })
    return copy
  }, [users, directPreviews])

  // ✅ “Streaming” search: filter updates on every keystroke (instant)
  const filteredUsers = useMemo(() => {
    const q = normalize(userSearch)
    if (!q) return sortedUsers
    return sortedUsers.filter((u) => {
      const hay = `${u.name} ${u.email}`.toLowerCase()
      return hay.includes(q)
    })
  }, [sortedUsers, userSearch])

  // Helpful: when you switch to Direct, focus search box
  useEffect(() => {
    if (mode !== 'direct') return
    window.setTimeout(() => userSearchInputRef.current?.focus(), 0)
  }, [mode])

  if (loading) {
    return (
      <Card>
        <CardContent>
          <p className="text-sm text-slate-500">Loading messages…</p>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent>
          <p className="text-sm text-rose-600">{error}</p>
          <Button className="mt-3" variant="secondary" onClick={() => void loadInitial()}>
            Retry
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-slate-900">Messages</h1>
          <p className="mt-1 text-sm text-slate-500">
            Direct user messaging and global open chat for all authenticated users.
          </p>
        </div>

        <div className="flex w-full items-center justify-start sm:w-auto">
          <div className="inline-flex w-full rounded-xl border border-slate-200 bg-white p-1 sm:w-auto">
            <button
              type="button"
              onClick={() => setMode('global')}
              className={[
                'relative w-1/2 rounded-lg px-3 py-2 text-sm font-medium transition sm:w-auto',
                mode === 'global' ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-50',
              ].join(' ')}
            >
              Global
              {hasUnseenGlobal ? (
                <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-rose-500" aria-label="Unseen messages" />
              ) : null}
            </button>

            <button
              type="button"
              onClick={() => setMode('direct')}
              className={[
                'relative w-1/2 rounded-lg px-3 py-2 text-sm font-medium transition sm:w-auto',
                mode === 'direct' ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-50',
              ].join(' ')}
            >
              Direct
              {Object.values(directPreviews).some((p) => p.hasUnseen) ? (
                <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-rose-500" aria-label="Unseen messages" />
              ) : null}
            </button>
          </div>
        </div>
      </div>

      {mode === 'global' ? (
        <Card>
          <CardHeader>
            <h2 className="text-lg font-semibold text-slate-900">Global Chat</h2>
            <p className="mt-1 text-sm text-slate-500">Shared room visible to every authenticated user.</p>
          </CardHeader>

          <CardContent className="space-y-4">
            {globalLoading ? <p className="text-sm text-slate-500">Loading global messages…</p> : renderMessages(globalMessages)}
            {globalError ? <p className="text-sm text-rose-600">{globalError}</p> : null}

            <form
              className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white p-2"
              onSubmit={(event) => void sendMessage(event, 'global')}
            >
              <Input
                value={globalInput}
                onChange={(event) => setGlobalInput(event.target.value)}
                placeholder="Type a message to everyone…"
              />
              <Button type="submit" disabled={sending || !globalRoomId}>
                Send
              </Button>
            </form>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          <Card className="lg:col-span-4">
            <CardHeader>
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between gap-3">
                  <h2 className="text-lg font-semibold text-slate-900">Chats</h2>
                  <div className="text-xs text-slate-500">{users.length} total</div>
                </div>

                {/* ✅ Streaming search bar */}
                <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white p-2">
                  <Input
                    ref={userSearchInputRef}
                    value={userSearch}
                    onChange={(e) => setUserSearch(e.target.value)}
                    placeholder="Search users (name or email)…"
                  />
                  {userSearch ? (
                    <button
                      type="button"
                      onClick={() => setUserSearch('')}
                      className="rounded-lg px-2 py-1 text-xs text-slate-600 hover:bg-slate-50"
                    >
                      Clear
                    </button>
                  ) : null}
                </div>

                {userSearch ? (
                  <div className="text-xs text-slate-500">
                    Showing {filteredUsers.length} result{filteredUsers.length === 1 ? '' : 's'}
                  </div>
                ) : null}
              </div>
            </CardHeader>

            <CardContent>
              <div className="max-h-[32rem] space-y-2 overflow-y-auto pr-1">
                {filteredUsers.length === 0 ? (
                  <p className="text-sm text-slate-500">No matches. Try a different name or email.</p>
                ) : null}

                {filteredUsers.map((chatUser) => {
                  const active = selectedUser?.id === chatUser.id
                  const preview = directPreviews[chatUser.id]
                  const hasUnseen = preview?.hasUnseen ?? false

                  return (
                    <button
                      key={chatUser.id}
                      className={[
                        'relative w-full rounded-xl border px-3 py-3 text-left text-sm transition',
                        active
                          ? 'border-slate-900 bg-slate-900 text-white'
                          : hasUnseen
                            ? 'border-emerald-400 bg-white text-slate-900 shadow-[0_0_0_3px_rgba(52,211,153,0.25)]'
                            : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
                      ].join(' ')}
                      onClick={() => setSelectedUser(chatUser)}
                      type="button"
                    >
                      {hasUnseen ? (
                        <span
                          className="absolute right-3 top-3 h-2.5 w-2.5 rounded-full bg-rose-500"
                          aria-label="Unseen messages"
                        />
                      ) : null}

                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className={['truncate font-semibold', hasUnseen ? 'text-emerald-700' : ''].join(' ')}>
                            {chatUser.name}
                          </div>
                          <div className={`truncate text-xs ${active ? 'text-slate-200' : 'text-slate-500'}`}>
                            {chatUser.email}
                          </div>

                          <div className={`mt-2 truncate text-xs ${hasUnseen ? 'text-emerald-700' : 'text-slate-500'}`}>
                            {preview?.latestText ? preview.latestText : 'No messages yet.'}
                          </div>
                        </div>

                        <div
                          className={[
                            'h-8 w-8 shrink-0 rounded-full grid place-items-center text-xs font-semibold',
                            active ? 'bg-white/10 text-white' : 'bg-slate-100 text-slate-700',
                          ].join(' ')}
                          aria-hidden="true"
                        >
                          {chatUser.name
                            .split(' ')
                            .filter(Boolean)
                            .slice(0, 2)
                            .map((p) => p[0]?.toUpperCase())
                            .join('')}
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>
            </CardContent>
          </Card>

          <Card className="lg:col-span-8">
            <CardHeader>
              <div className="flex flex-col gap-1">
                <h2 className="text-lg font-semibold text-slate-900">{directTitle}</h2>
                <p className="text-sm text-slate-500">
                  {selectedUser ? `Private room between you and ${selectedUser.name}.` : 'Pick a user from the list to start chatting.'}
                </p>
              </div>
            </CardHeader>

            <CardContent className="space-y-4">
              {directLoading ? <p className="text-sm text-slate-500">Loading direct messages…</p> : renderMessages(directMessages)}
              {directError ? <p className="text-sm text-rose-600">{directError}</p> : null}

              <form
                className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white p-2"
                onSubmit={(event) => void sendMessage(event, 'direct')}
              >
                <Input
                  value={directInput}
                  onChange={(event) => setDirectInput(event.target.value)}
                  placeholder={selectedUser ? `Message ${selectedUser.name}…` : 'Select a user first'}
                  disabled={!selectedUser}
                />
                <Button type="submit" disabled={sending || !selectedUser || !directRoomId}>
                  Send
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
