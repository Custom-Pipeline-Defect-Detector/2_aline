import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError, apiFetch } from '../api'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import Input from '../components/ui/Input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table'
import { useToast } from '../components/Toast'

interface CustomerItem {
  id: number
  name: string
  status: string
  industry?: string
  active_projects: number
  last_activity_at?: string
}

const STATUS_OPTIONS = ['lead', 'active', 'on_hold', 'inactive'] as const

const INDUSTRY_OPTIONS = [
  'manufacturing',
  'automotive',
  'aerospace',
  'energy',
  'construction',
  'consumer_goods',
  'logistics',
  'other',
] as const

function cx(...classes: Array<string | false | undefined | null>) {
  return classes.filter(Boolean).join(' ')
}

function statusBadgeVariant(status: string) {
  if (status === 'active') return 'success'
  if (status === 'on_hold') return 'warning'
  if (status === 'inactive') return 'default'
  return 'info' // lead + anything else
}

export default function CustomersPage() {
  const [customers, setCustomers] = useState<CustomerItem[]>([])
  const [search, setSearch] = useState('')
  const [showNewCustomer, setShowNewCustomer] = useState(false)

  const [newCustomer, setNewCustomer] = useState({
    name: '',
    status: 'lead',
    industry: '',
    tags: '',
    aliases: '',
    notes: '',
  })

  const [customIndustry, setCustomIndustry] = useState('')
  const [contacts, setContacts] = useState<Array<{ name: string; email: string; role_title: string; phone: string }>>([])

  const [creating, setCreating] = useState(false)
  const [loadingCustomers, setLoadingCustomers] = useState(false)

  // Inline editing state (optional)
  const [updatingCustomerId, setUpdatingCustomerId] = useState<number | null>(null)

  const navigate = useNavigate()
  const toast = useToast()

  const loadCustomers = useCallback(async () => {
    setLoadingCustomers(true)
    try {
      const data = (await apiFetch('/customers')) as CustomerItem[]
      setCustomers(data)
    } catch (error) {
      setCustomers([])
      const description = error instanceof Error ? error.message : 'Unable to load customers'
      toast.push({ title: 'Load failed', description, variant: 'error' })
    } finally {
      setLoadingCustomers(false)
    }
  }, [toast])

  useEffect(() => {
    void loadCustomers()
  }, [loadCustomers])

  // ESC closes modal
  useEffect(() => {
    if (!showNewCustomer) return
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setShowNewCustomer(false)
        resetNewCustomer()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showNewCustomer])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return customers
    return customers.filter((c) => {
      return (
        c.name.toLowerCase().includes(q) ||
        (c.industry ?? '').toLowerCase().includes(q) ||
        (c.status ?? '').toLowerCase().includes(q)
      )
    })
  }, [customers, search])

  const resetNewCustomer = () => {
    setNewCustomer({ name: '', status: 'lead', industry: '', tags: '', aliases: '', notes: '' })
    setCustomIndustry('')
    setContacts([])
  }

  const addContact = () => {
    setContacts((prev) => [...prev, { name: '', email: '', role_title: '', phone: '' }])
  }

  const updateContact = (index: number, field: string, value: string) => {
    setContacts((prev) => prev.map((c, idx) => (idx === index ? { ...c, [field]: value } : c)))
  }

  const removeContact = (index: number) => {
    setContacts((prev) => prev.filter((_, idx) => idx !== index))
  }

  const createCustomer = async () => {
    if (!newCustomer.name.trim() || creating) return

    const finalIndustry =
      newCustomer.industry === 'other' ? (customIndustry.trim() || 'other') : newCustomer.industry.trim()

    const payload = {
      name: newCustomer.name.trim(),
      status: newCustomer.status,
      industry: finalIndustry || undefined,
      tags: newCustomer.tags
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean),
      aliases: newCustomer.aliases
        .split(',')
        .map((alias) => alias.trim())
        .filter(Boolean),
      notes: newCustomer.notes.trim() || undefined,
      contacts: contacts
        .map((contact) => ({
          name: contact.name.trim(),
          email: contact.email.trim() || undefined,
          role_title: contact.role_title.trim() || undefined,
          phone: contact.phone.trim() || undefined,
        }))
        .filter((contact) => contact.name),
    }

    setCreating(true)
    try {
      await apiFetch('/customers', { method: 'POST', body: JSON.stringify(payload) })
      toast.push({ title: 'Customer created', variant: 'success' })
      resetNewCustomer()
      setShowNewCustomer(false)
      await loadCustomers()
    } catch (err) {
      toast.push({
        title: 'Create failed',
        description: err instanceof ApiError && err.status === 403 ? "You don't have access" : 'Please try again.',
        variant: 'error',
      })
    } finally {
      setCreating(false)
    }
  }

  // Optional inline update for status/industry in table
  const patchCustomer = async (id: number, patch: Partial<CustomerItem>) => {
    setUpdatingCustomerId(id)
    try {
      const updated = (await apiFetch(`/customers/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(patch),
      })) as CustomerItem

      setCustomers((prev) => prev.map((c) => (c.id === id ? { ...c, ...updated } : c)))
      await loadCustomers()
      toast.push({ title: 'Customer updated', variant: 'success' })
    } catch (err) {
      toast.push({
        title: 'Update failed',
        description: err instanceof ApiError && err.status === 403 ? "You don't have access" : 'Please try again.',
        variant: 'error',
      })
    } finally {
      setUpdatingCustomerId(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="text-xs text-slate-400">
        <Link className="hover:text-slate-600" to="/dashboard">
          Dashboard
        </Link>{' '}
        / Customers
      </div>

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700 shadow-sm">
            <span className="h-2 w-2 rounded-full bg-sky-400 shadow-[0_0_10px_rgba(56,189,248,0.75)]" />
            CRM
          </div>
          <h1 className="mt-3 text-2xl font-semibold text-slate-900">Automation Clients</h1>
          <p className="mt-1 text-sm text-slate-500">Track automation development client health and active projects.</p>
        </div>

        <Button onClick={() => setShowNewCustomer(true)}>New Customer</Button>
      </div>

      {loadingCustomers ? <div className="text-xs text-slate-500">Refreshing customers…</div> : null}

      <div className="flex items-center justify-between">
        <Input
          type="search"
          placeholder="Search customers, status, industry…"
          className="max-w-sm"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </div>

      <Card className="overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Industry</TableHead>
              <TableHead>Active Projects</TableHead>
              <TableHead>Last Activity</TableHead>
            </TableRow>
          </TableHeader>

          <TableBody>
            {filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-sm text-slate-500">
                  No customers found.
                </TableCell>
              </TableRow>
            ) : null}

            {filtered.map((customer) => (
              <TableRow key={customer.id} className="hover:bg-slate-50">
                {/* Name click navigates */}
                <TableCell
                  className="cursor-pointer font-medium"
                  onClick={() => navigate(`/customers/${customer.id}`)}
                >
                  {customer.name}
                </TableCell>

                {/* Status dropdown */}
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Badge variant={statusBadgeVariant(customer.status)}>{customer.status}</Badge>

                    <select
                      className={cx(
                        'rounded-xl border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700',
                        'shadow-sm focus:outline-none focus:ring-2 focus:ring-sky-300/40'
                      )}
                      value={customer.status}
                      disabled={updatingCustomerId === customer.id}
                      onChange={(e) => void patchCustomer(customer.id, { status: e.target.value })}
                      onClick={(e) => e.stopPropagation()}
                    >
                      {STATUS_OPTIONS.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </div>
                </TableCell>

                {/* Industry dropdown */}
                <TableCell className="text-slate-500">
                  <select
                    className={cx(
                      'w-full max-w-[220px] rounded-xl border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700',
                      'shadow-sm focus:outline-none focus:ring-2 focus:ring-sky-300/40'
                    )}
                    value={customer.industry ?? ''}
                    disabled={updatingCustomerId === customer.id}
                    onChange={(e) => void patchCustomer(customer.id, { industry: e.target.value || undefined })}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <option value="">—</option>
                    {INDUSTRY_OPTIONS.map((i) => (
                      <option key={i} value={i}>
                        {i}
                      </option>
                    ))}
                  </select>
                </TableCell>

                <TableCell>{customer.active_projects}</TableCell>

                <TableCell className="text-xs text-slate-400">
                  {customer.last_activity_at ? new Date(customer.last_activity_at).toLocaleDateString() : 'No activity'}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {filtered.length === 0 ? (
        <Card className="p-10 text-center text-sm text-slate-400">No customers found. Try adjusting your search.</Card>
      ) : null}

      {/* Modal */}
      {showNewCustomer ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-sm"
          onClick={() => {
            setShowNewCustomer(false)
            resetNewCustomer()
          }}
        >
          <Card className="relative w-full max-w-2xl p-6" onClick={(e) => e.stopPropagation()}>
            {/* glow edge */}
            <span
              className="pointer-events-none absolute -inset-1 rounded-3xl bg-gradient-to-r from-sky-400/10 via-cyan-400/12 to-fuchsia-400/10 blur-xl"
              aria-hidden="true"
            />

            <div className="relative flex items-center justify-between">
              <div>
                <div className="text-xs uppercase text-slate-400">New customer</div>
                <div className="text-lg font-semibold text-slate-900">Add customer details</div>
              </div>
              <button
                className="text-sm font-semibold text-slate-500 hover:text-slate-700"
                onClick={() => {
                  setShowNewCustomer(false)
                  resetNewCustomer()
                }}
              >
                Close
              </button>
            </div>

            <div className="relative mt-4 grid gap-4 md:grid-cols-2">
              <div className="md:col-span-2">
                <label className="text-xs uppercase text-slate-400">Name</label>
                <Input
                  className="mt-2"
                  value={newCustomer.name}
                  onChange={(event) => setNewCustomer({ ...newCustomer, name: event.target.value })}
                />
              </div>

              <div>
                <label className="text-xs uppercase text-slate-400">Status</label>
                <select
                  className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-sky-300/40"
                  value={newCustomer.status}
                  onChange={(event) => setNewCustomer({ ...newCustomer, status: event.target.value })}
                >
                  {STATUS_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs uppercase text-slate-400">Industry</label>
                <select
                  className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-sky-300/40"
                  value={newCustomer.industry}
                  onChange={(event) => setNewCustomer({ ...newCustomer, industry: event.target.value })}
                >
                  <option value="">(unset)</option>
                  {INDUSTRY_OPTIONS.map((i) => (
                    <option key={i} value={i}>
                      {i}
                    </option>
                  ))}
                </select>

                {newCustomer.industry === 'other' ? (
                  <Input
                    className="mt-2"
                    placeholder="Custom industry…"
                    value={customIndustry}
                    onChange={(e) => setCustomIndustry(e.target.value)}
                  />
                ) : null}
              </div>

              <div className="md:col-span-2">
                <label className="text-xs uppercase text-slate-400">Tags</label>
                <Input
                  className="mt-2"
                  placeholder="Comma-separated"
                  value={newCustomer.tags}
                  onChange={(event) => setNewCustomer({ ...newCustomer, tags: event.target.value })}
                />
              </div>

              <div className="md:col-span-2">
                <label className="text-xs uppercase text-slate-400">Aliases</label>
                <Input
                  className="mt-2"
                  placeholder="Comma-separated"
                  value={newCustomer.aliases}
                  onChange={(event) => setNewCustomer({ ...newCustomer, aliases: event.target.value })}
                />
              </div>

              <div className="md:col-span-2">
                <label className="text-xs uppercase text-slate-400">Notes</label>
                <textarea
                  className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-sky-300/40"
                  rows={3}
                  value={newCustomer.notes}
                  onChange={(event) => setNewCustomer({ ...newCustomer, notes: event.target.value })}
                />
              </div>
            </div>

            <div className="relative mt-6 space-y-3">
              <div className="flex items-center justify-between">
                <div className="text-sm font-semibold text-slate-900">Contacts</div>
                <Button variant="secondary" onClick={addContact}>
                  Add contact
                </Button>
              </div>

              {contacts.length === 0 ? <div className="text-sm text-slate-400">No contacts added yet.</div> : null}

              <div className="space-y-3">
                {contacts.map((contact, index) => (
                  <div key={index} className="rounded-2xl border border-slate-100 bg-white p-3 shadow-sm">
                    <div className="flex items-center justify-between">
                      <div className="text-xs uppercase text-slate-400">Contact {index + 1}</div>
                      <button className="text-xs font-semibold text-rose-500 hover:underline" onClick={() => removeContact(index)}>
                        Remove
                      </button>
                    </div>
                    <div className="mt-2 grid gap-2 md:grid-cols-2">
                      <Input
                        placeholder="Name"
                        value={contact.name}
                        onChange={(event) => updateContact(index, 'name', event.target.value)}
                      />
                      <Input
                        placeholder="Email"
                        value={contact.email}
                        onChange={(event) => updateContact(index, 'email', event.target.value)}
                      />
                      <Input
                        placeholder="Role"
                        value={contact.role_title}
                        onChange={(event) => updateContact(index, 'role_title', event.target.value)}
                      />
                      <Input
                        placeholder="Phone"
                        value={contact.phone}
                        onChange={(event) => updateContact(index, 'phone', event.target.value)}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative mt-6 flex items-center justify-end gap-3">
              <Button
                variant="secondary"
                onClick={() => {
                  setShowNewCustomer(false)
                  resetNewCustomer()
                }}
                disabled={creating}
              >
                Cancel
              </Button>
              <Button onClick={createCustomer} disabled={!newCustomer.name.trim() || creating}>
                {creating ? 'Saving…' : 'Save customer'}
              </Button>
            </div>
          </Card>
        </div>
      ) : null}
    </div>
  )
}

// TODO Phase 2: CRM pipeline with opportunities, quotes, and purchase orders.
