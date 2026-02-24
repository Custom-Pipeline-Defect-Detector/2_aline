import React from 'react'

type Variant = 'default' | 'success' | 'warning' | 'danger' | 'info'

const variants: Record<Variant, string> = {
  default: 'bg-slate-100 text-slate-600',
  success: 'bg-emerald-100 text-emerald-600',
  warning: 'bg-amber-100 text-amber-600',
  danger: 'bg-rose-100 text-rose-600',
  info: 'bg-blue-100 text-blue-600',
}

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: Variant
}

export default function Badge({ variant = 'default', className = '', ...props }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${variants[variant]} ${className}`}
      {...props}
    />
  )
}
