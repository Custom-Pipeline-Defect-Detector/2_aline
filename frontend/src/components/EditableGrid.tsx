import { useEffect, useMemo, useRef, useState } from 'react'
import { AgGridReact } from 'ag-grid-react'
import type { ColDef, GridApi } from 'ag-grid-community'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-quartz.css'

import Button from './ui/Button'
import { useToast } from './Toast'

export interface EditableGridColumn {
  field: string
  headerName: string
  editable?: boolean
  required?: boolean
  width?: number
}

interface EditableGridProps<T extends Record<string, any>> {
  title: string
  rows: T[]
  columns: EditableGridColumn[]
  onSave: (rows: T[]) => Promise<void>
  onDelete?: (ids: number[]) => Promise<void>
  statusField?: string
  readOnly?: boolean
}

const isValidDate = (value: string) => (!value ? true : /^\d{4}-\d{2}-\d{2}$/.test(value))

export default function EditableGrid<T extends Record<string, any>>({
  title,
  rows,
  columns,
  onSave,
  onDelete,
  statusField,
  readOnly = false,
}: EditableGridProps<T>) {
  const apiRef = useRef<GridApi | null>(null)
  const toast = useToast()
  const [saving, setSaving] = useState(false)
  const [bulkStatus, setBulkStatus] = useState('')
  const [rowData, setRowData] = useState<T[]>(rows)

  useEffect(() => setRowData(rows), [rows])

  const columnDefs = useMemo<ColDef[]>(
    () =>
      columns.map((column) => ({
        field: column.field,
        headerName: column.headerName,
        editable: readOnly ? false : (column.editable ?? true),
        width: column.width,
        flex: column.width ? undefined : 1,
        sortable: true,
        filter: true,
      })),
    [columns, readOnly]
  )

  const addRow = () => {
    const emptyRow: Record<string, any> = {}
    columns.forEach((col) => {
      emptyRow[col.field] = ''
    })
    setRowData((current) => [...current, emptyRow as T])
  }

  const removeSelected = () => {
    const selected = apiRef.current?.getSelectedRows() ?? []
    if (!selected.length) return
    setRowData((current) => current.filter((row) => !selected.includes(row)))
    if (onDelete) {
      const ids = selected.map((row) => Number(row.id)).filter(Boolean)
      if (ids.length) {
        onDelete(ids).catch(() => {
          toast.push({ title: 'Delete failed', description: 'Could not remove selected rows.', variant: 'error' })
        })
      }
    }
  }

  const applyBulkStatus = () => {
    if (!statusField || !bulkStatus) return
    const selected = apiRef.current?.getSelectedRows() ?? []
    selected.forEach((row) => {
      row[statusField] = bulkStatus
    })
    setRowData([...rowData])
  }

  const validateRows = (data: T[]) => {
    const requiredFields = columns.filter((column) => column.required).map((column) => column.field)
    for (const row of data) {
      for (const field of requiredFields) {
        if (row[field] === null || row[field] === undefined || row[field] === '') return `Missing required field: ${field}`
      }
      for (const key of Object.keys(row)) {
        if (key.includes('date') && row[key] && !isValidDate(String(row[key]))) return `Invalid date format for ${key}. Use YYYY-MM-DD.`
      }
    }
    return ''
  }

  const save = async () => {
    const error = validateRows(rowData)
    if (error) {
      toast.push({ title: 'Validation error', description: error, variant: 'error' })
      return
    }
    setSaving(true)
    try {
      await onSave(rowData)
      toast.push({ title: `${title} saved`, variant: 'success' })
    } catch {
      toast.push({ title: 'Save failed', description: 'Please try again.', variant: 'error' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm font-semibold text-slate-900">{title}</div>
        {!readOnly ? (
          <div className="flex flex-wrap items-center gap-2">
            {statusField ? (
              <>
                <input
                  className="rounded-lg border border-slate-200 px-3 py-1 text-xs"
                  placeholder="Bulk status"
                  value={bulkStatus}
                  onChange={(event) => setBulkStatus(event.target.value)}
                />
                <Button variant="secondary" size="sm" onClick={applyBulkStatus}>Apply status</Button>
              </>
            ) : null}
            <Button variant="secondary" size="sm" onClick={addRow}>Add row</Button>
            <Button variant="ghost" size="sm" onClick={removeSelected}>Remove selected</Button>
            <Button size="sm" onClick={save} disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</Button>
          </div>
        ) : (
          <div className="text-xs text-slate-500">Read-only view</div>
        )}
      </div>
      <div className="ag-theme-quartz" style={{ height: 360, width: '100%' }}>
        <AgGridReact
          rowData={rowData}
          columnDefs={columnDefs}
          rowSelection={{ mode: 'multiRow', enableClickSelection: false }}
          cellSelection={true}
          onGridReady={(params) => {
            apiRef.current = params.api
          }}
        />
      </div>
    </div>
  )
}
