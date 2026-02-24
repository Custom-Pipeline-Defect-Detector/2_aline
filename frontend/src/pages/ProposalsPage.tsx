import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api'
import Badge from '../components/ui/Badge'
import { Card } from '../components/ui/Card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table'

interface ProposalItem {
  id: number
  target_table: string
  status: string
  created_at: string
}

export default function ProposalsPage() {
  const [proposals, setProposals] = useState<ProposalItem[]>([])
  const [status, setStatus] = useState('pending')
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    apiFetch(`/proposals?status=${status}`)
      .then(setProposals)
      .catch(() => setProposals([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [status])

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Proposals</h1>
          <p className="text-sm text-slate-500">Review and approve extracted actions.</p>
        </div>
        <select
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
          value={status}
          onChange={(event) => setStatus(event.target.value)}
        >
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>
      <Card className="overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>Target</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-sm text-slate-500">
                  Loading proposals...
                </TableCell>
              </TableRow>
            ) : null}
            {!loading && proposals.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-sm text-slate-500">
                  No proposals found for this status.
                </TableCell>
              </TableRow>
            ) : null}
            {!loading
              ? proposals.map((proposal) => (
                  <TableRow key={proposal.id}>
                    <TableCell className="font-medium">#{proposal.id}</TableCell>
                    <TableCell>{proposal.target_table}</TableCell>
                    <TableCell>
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
                    </TableCell>
                    <TableCell>{new Date(proposal.created_at).toLocaleString()}</TableCell>
                    <TableCell>
                      <Link
                        className="inline-flex items-center rounded-lg px-3 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-100"
                        to={`/proposals/${proposal.id}`}
                      >
                        Review
                      </Link>
                    </TableCell>
                  </TableRow>
                ))
              : null}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
