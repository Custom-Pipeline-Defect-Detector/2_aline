import React from 'react'

interface TableProps extends React.TableHTMLAttributes<HTMLTableElement> {}
interface SectionProps extends React.HTMLAttributes<HTMLTableSectionElement> {}
interface RowProps extends React.HTMLAttributes<HTMLTableRowElement> {}
interface CellProps extends React.ThHTMLAttributes<HTMLTableCellElement> {}
interface DataCellProps extends React.TdHTMLAttributes<HTMLTableCellElement> {}

export function Table({ className = '', ...props }: TableProps) {
  return <table className={`w-full text-sm ${className}`} {...props} />
}

export function TableHeader({ className = '', ...props }: SectionProps) {
  return <thead className={`bg-slate-50 text-left text-xs uppercase text-slate-400 ${className}`} {...props} />
}

export function TableBody({ className = '', ...props }: SectionProps) {
  return <tbody className={className} {...props} />
}

export function TableRow({ className = '', ...props }: RowProps) {
  return <tr className={`border-t ${className}`} {...props} />
}

export function TableHead({ className = '', ...props }: CellProps) {
  return <th className={`px-4 py-3 font-semibold ${className}`} {...props} />
}

export function TableCell({ className = '', ...props }: DataCellProps) {
  return <td className={`px-4 py-3 ${className}`} {...props} />
}
