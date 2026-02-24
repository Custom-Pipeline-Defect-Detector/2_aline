import React from 'react'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Card({ className = '', ...props }: CardProps) {
  return <div className={`rounded-xl border border-slate-200 bg-white shadow-sm ${className}`} {...props} />
}

export function CardHeader({ className = '', ...props }: CardProps) {
  return <div className={`border-b border-slate-100 px-4 py-3 ${className}`} {...props} />
}

export function CardTitle({ className = '', ...props }: CardProps) {
  return <div className={`text-sm font-semibold uppercase tracking-wide text-slate-500 ${className}`} {...props} />
}

export function CardContent({ className = '', ...props }: CardProps) {
  return <div className={`px-4 py-4 ${className}`} {...props} />
}
