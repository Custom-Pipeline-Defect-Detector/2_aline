import { useEffect, useMemo, useState } from 'react'
import { ApiError, apiFetch } from '../api'
import { useAuth } from '../auth/AuthContext'
import EditableGrid from '../components/EditableGrid'
import { Card } from '../components/ui/Card'
import Button from '../components/ui/Button'

interface TaskRow {
  id?: number
  project_code?: string
  title: string
  owner_id?: number | null
  due_date?: string | null
  status?: string
  source_doc_id?: number | null
  created_at?: string
}

interface WorkLogRow {
  id?: number
  project_code?: string
  user_id?: number | null
  date: string
  summary: string
  derived_from_doc_id?: number | null
}

export default function WorkPage() {
  const [tasks, setTasks] = useState<TaskRow[]>([])
  const [workLogs, setWorkLogs] = useState<WorkLogRow[]>([])
  const [mineOnly, setMineOnly] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const { can } = useAuth()
  const canWrite = can('workWrite')

  const load = async () => {
    setLoading(true)
    try {
      setError('')
      const [taskData, worklogData] = await Promise.all([
        apiFetch(`/tasks${mineOnly ? '?mine=true' : ''}`),
        apiFetch('/worklogs'),
      ])
      setTasks(taskData)
      setWorkLogs(worklogData)
    } catch (err) {
      setTasks([])
      setWorkLogs([])
      setError(err instanceof ApiError && err.status === 403 ? "You don\'t have access to this action." : 'Unable to load work data.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [mineOnly])

  const taskColumns = useMemo(
    () => [
      { field: 'project_code', headerName: 'Project', required: true },
      { field: 'title', headerName: 'Title', required: true },
      { field: 'owner_id', headerName: 'Owner' },
      { field: 'due_date', headerName: 'Due date' },
      { field: 'status', headerName: 'Status' },
      { field: 'source_doc_id', headerName: 'Source doc' },
      { field: 'created_at', headerName: 'Last updated', editable: false },
    ],
    []
  )

  const worklogColumns = useMemo(
    () => [
      { field: 'user_id', headerName: 'User' },
      { field: 'project_code', headerName: 'Project', required: true },
      { field: 'date', headerName: 'Date', required: true },
      { field: 'summary', headerName: 'Summary', required: true },
      { field: 'derived_from_doc_id', headerName: 'Doc ref' },
    ],
    []
  )

  const saveTasks = async (rows: TaskRow[]) => {
    const updates = rows.map((row) => {
      if (row.id) {
        return apiFetch(`/tasks/${row.id}`, {
          method: 'PATCH',
          body: JSON.stringify({
            project_code: row.project_code,
            title: row.title,
            owner_id: row.owner_id || null,
            due_date: row.due_date || null,
            status: row.status || 'open',
            source_doc_id: row.source_doc_id || null,
          }),
        })
      }
      return apiFetch('/tasks', {
        method: 'POST',
        body: JSON.stringify({
          project_code: row.project_code,
          title: row.title,
          owner_id: row.owner_id || null,
          due_date: row.due_date || null,
          status: row.status || 'open',
          source_doc_id: row.source_doc_id || null,
        }),
      })
    })
    await Promise.all(updates)
    await load()
  }

  const deleteTasks = async (ids: number[]) => {
    await Promise.all(ids.map((id) => apiFetch(`/tasks/${id}`, { method: 'DELETE' })))
    await load()
  }

  const saveWorkLogs = async (rows: WorkLogRow[]) => {
    const updates = rows.map((row) => {
      if (row.id) {
        return apiFetch(`/worklogs/${row.id}`, {
          method: 'PATCH',
          body: JSON.stringify({
            project_code: row.project_code,
            user_id: row.user_id || null,
            date: row.date,
            summary: row.summary,
            derived_from_doc_id: row.derived_from_doc_id || null,
          }),
        })
      }
      return apiFetch('/worklogs', {
        method: 'POST',
        body: JSON.stringify({
          project_code: row.project_code,
          user_id: row.user_id || null,
          date: row.date,
          summary: row.summary,
          derived_from_doc_id: row.derived_from_doc_id || null,
        }),
      })
    })
    await Promise.all(updates)
    await load()
  }

  const deleteWorkLogs = async (ids: number[]) => {
    await Promise.all(ids.map((id) => apiFetch(`/worklogs/${id}`, { method: 'DELETE' })))
    await load()
  }

  if (loading) {
    return <div className="h-40 animate-pulse rounded-xl bg-slate-100" />
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Automation Tasks</h1>
          <p className="text-sm text-slate-500">Track automation development tasks and daily work logs.</p>
        </div>
        <Button variant={mineOnly ? 'secondary' : 'ghost'} onClick={() => setMineOnly((prev) => !prev)}>
          {mineOnly ? 'Showing My Work' : 'My Work'}
        </Button>
      </div>

      {error ? <Card className="p-3 text-sm text-amber-700">{error}</Card> : null}

      <Card className="p-4">
        <EditableGrid
          title="Tasks"
          rows={tasks}
          columns={taskColumns}
          onSave={saveTasks}
          onDelete={deleteTasks}
          statusField="status"
          readOnly={!canWrite}
        />
      </Card>

      <Card className="p-4">
        <EditableGrid
          title="Work logs"
          rows={workLogs}
          columns={worklogColumns}
          onSave={saveWorkLogs}
          onDelete={deleteWorkLogs}
          readOnly={!canWrite}
        />
      </Card>
    </div>
  )
}
