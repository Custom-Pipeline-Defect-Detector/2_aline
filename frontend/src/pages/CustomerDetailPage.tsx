import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiFetch } from '../api'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import Input from '../components/ui/Input'
import { useToast } from '../components/Toast'

type TabKey = 'overview' | 'contacts' | 'projects' | 'documents' | 'activity'

interface Contact {
  id: number
  name: string
  email?: string
  role_title?: string
  phone?: string
}

interface CustomerDetail {
  id: number
  name: string
  status: string
  industry?: string
  notes?: string
  tags: string[]
  contacts: Contact[]
  projects?: { id: number; name: string; status: string; health: string }[]
  documents_count: number
}

export default function CustomerDetailPage() {
  const { id } = useParams()
  const [customer, setCustomer] = useState<CustomerDetail | null>(null)
  const [draft, setDraft] = useState<CustomerDetail | null>(null)
  const [tab, setTab] = useState<TabKey>('overview')
  const [newContact, setNewContact] = useState({ name: '', email: '', role_title: '', phone: '' })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const toast = useToast()

  const load = () => {
    if (!id) return
    setLoading(true)
    setError('')
    apiFetch(`/customers/${id}`)
      .then((data) => {
        setCustomer(data)
        setDraft(data)
      })
      .catch(() => {
        setCustomer(null)
        setDraft(null)
        setError('Unable to load customer details.')
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [id])

  const updateCustomer = async (field: string, value: any) => {
    if (!id) return
    setSaving(true)
    try {
      const updated = await apiFetch(`/customers/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ [field]: value }),
      })
      setCustomer(updated)
      setDraft(updated)
    } catch (err) {
      toast.push({
        title: 'Update failed',
        description: err instanceof Error ? err.message : 'Please try again.',
        variant: 'error',
      })
      load()
    } finally {
      setSaving(false)
    }
  }

  const addContact = async () => {
    if (!id || !newContact.name) return
    try {
      await apiFetch(`/customers/${id}/contacts`, {
        method: 'POST',
        body: JSON.stringify(newContact),
      })
      toast.push({ title: 'Contact added', variant: 'success' })
      setNewContact({ name: '', email: '', role_title: '', phone: '' })
      load()
    } catch (err) {
      toast.push({
        title: 'Add contact failed',
        description: err instanceof Error ? err.message : 'Please try again.',
        variant: 'error',
      })
    }
  }

  const removeContact = async (contactId: number) => {
    if (!id) return
    try {
      await apiFetch(`/customers/${id}/contacts/${contactId}`, { method: 'DELETE' })
      toast.push({ title: 'Contact removed', variant: 'info' })
      load()
    } catch (err) {
      toast.push({
        title: 'Remove contact failed',
        description: err instanceof Error ? err.message : 'Please try again.',
        variant: 'error',
      })
    }
  }

  if (loading) {
    return (
      <Card className="p-6 text-center">
        <div className="text-sm text-slate-500">Loading customer...</div>
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

  if (!customer || !draft) {
    return (
      <Card className="p-6 text-center">
        <div className="text-sm text-slate-500">Customer not found.</div>
        <Button className="mt-4" onClick={() => window.history.back()}>
          Back
        </Button>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <div className="text-xs text-slate-400">
        <Link className="hover:text-slate-600" to="/customers">
          Customers
        </Link>{' '}
        / {customer.name}
      </div>
      <Card className="p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="text-xs uppercase text-slate-400">Customer</div>
            <Input
              className="mt-2 text-xl font-semibold"
              value={draft.name}
              disabled={saving}
              onChange={(event) => setDraft({ ...draft, name: event.target.value })}
              onBlur={() => {
                if (draft.name !== customer.name) {
                  void updateCustomer('name', draft.name)
                }
              }}
            />
          </div>
          <div className="flex items-center gap-2">
            <select
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
              value={draft.status}
              disabled={saving}
              onChange={(event) => {
                const next = event.target.value
                setDraft({ ...draft, status: next })
                void updateCustomer('status', next)
              }}
            >
              <option value="lead">Lead</option>
              <option value="active">Active</option>
              <option value="on_hold">On hold</option>
              <option value="inactive">Inactive</option>
            </select>
            <Button variant="secondary">Share</Button>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {(['overview', 'contacts', 'projects', 'documents', 'activity'] as TabKey[]).map((key) => (
            <button
              key={key}
              className={`rounded-full px-4 py-2 text-sm ${
                tab === key ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600'
              }`}
              onClick={() => setTab(key)}
            >
              {key}
            </button>
          ))}
        </div>
      </Card>

      {tab === 'overview' ? (
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="p-4">
            <div className="text-xs uppercase text-slate-400">Industry</div>
            <Input
              className="mt-3"
              value={draft.industry ?? ''}
              disabled={saving}
              onChange={(event) => setDraft({ ...draft, industry: event.target.value })}
              onBlur={() => {
                if ((draft.industry ?? '') !== (customer.industry ?? '')) {
                  void updateCustomer('industry', draft.industry || null)
                }
              }}
            />
          </Card>
          <Card className="p-4">
            <div className="text-xs uppercase text-slate-400">Tags</div>
            <Input
              className="mt-3"
              value={(draft.tags || []).join(', ')}
              disabled={saving}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  tags: event.target.value
                    .split(',')
                    .map((tag) => tag.trim())
                    .filter(Boolean),
                })
              }
              onBlur={() => {
                const currentTags = JSON.stringify(customer.tags || [])
                const nextTags = JSON.stringify(draft.tags || [])
                if (currentTags !== nextTags) {
                  void updateCustomer('tags', draft.tags || [])
                }
              }}
            />
          </Card>
          <Card className="p-4 md:col-span-2">
            <div className="text-xs uppercase text-slate-400">Notes</div>
            <textarea
              className="mt-3 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
              rows={4}
              value={draft.notes ?? ''}
              disabled={saving}
              onChange={(event) => setDraft({ ...draft, notes: event.target.value })}
              onBlur={() => {
                if ((draft.notes ?? '') !== (customer.notes ?? '')) {
                  void updateCustomer('notes', draft.notes || null)
                }
              }}
            />
          </Card>
        </div>
      ) : null}

      {tab === 'contacts' ? (
        <div className="grid gap-4 md:grid-cols-2">
          {customer.contacts.length === 0 ? (
            <Card className="p-4 text-sm text-slate-400">No contacts added yet.</Card>
          ) : null}
          {customer.contacts.map((contact) => (
            <Card key={contact.id} className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-semibold">{contact.name}</div>
                  <div className="text-xs text-slate-400">{contact.role_title ?? 'Contact'}</div>
                </div>
                <button className="text-xs text-rose-500" onClick={() => removeContact(contact.id)}>
                  Remove
                </button>
              </div>
              <div className="mt-3 text-sm text-slate-600">
                {contact.email ?? 'No email'} · {contact.phone ?? 'No phone'}
              </div>
            </Card>
          ))}
          <Card className="p-4">
            <div className="text-sm font-semibold text-slate-900">Add contact</div>
            <div className="mt-3 space-y-2">
              <Input
                placeholder="Name"
                value={newContact.name}
                onChange={(event) => setNewContact({ ...newContact, name: event.target.value })}
              />
              <Input
                placeholder="Email"
                value={newContact.email}
                onChange={(event) => setNewContact({ ...newContact, email: event.target.value })}
              />
              <Input
                placeholder="Role"
                value={newContact.role_title}
                onChange={(event) => setNewContact({ ...newContact, role_title: event.target.value })}
              />
              <Input
                placeholder="Phone"
                value={newContact.phone}
                onChange={(event) => setNewContact({ ...newContact, phone: event.target.value })}
              />
              <Button className="w-full" onClick={addContact}>
                Add contact
              </Button>
            </div>
          </Card>
        </div>
      ) : null}

      {tab === 'projects' ? (
        <Card className="p-4">
          <div className="text-sm font-semibold text-slate-900">Linked projects</div>
          {customer.projects && customer.projects.length > 0 ? (
            <ul className="mt-4 space-y-2 text-sm">
              {customer.projects.map((project) => (
                <li key={project.id} className="flex items-center justify-between rounded-lg border border-slate-100 p-3">
                  <span>{project.name}</span>
                  <Badge
                    variant={
                      project.health === 'red' ? 'danger' : project.health === 'yellow' ? 'warning' : 'success'
                    }
                  >
                    {project.health}
                  </Badge>
                </li>
              ))}
            </ul>
          ) : (
            <div className="mt-4 rounded-lg border border-dashed border-slate-200 p-4 text-sm text-slate-400">
              No linked projects.
            </div>
          )}
        </Card>
      ) : null}

      {tab === 'documents' ? (
        <Card className="p-4">
          <div className="text-sm font-semibold text-slate-900">Documents</div>
          <div className="mt-3 text-sm text-slate-600">
            {customer.documents_count} documents linked. Check Documents to review items needing attention.
          </div>
        </Card>
      ) : null}

      {tab === 'activity' ? (
        <Card className="p-6 text-center text-sm text-slate-400">
          Activity feed coming soon. Automated audit events will appear here.
        </Card>
      ) : null}
    </div>
  )
}
