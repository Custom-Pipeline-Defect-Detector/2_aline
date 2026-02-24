import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import type { Role } from '../auth/permissions'

export default function RequireRoles({ roles, children }: { roles: Role[]; children: React.ReactElement }) {
  const { loading, roles: currentRoles } = useAuth()
  if (loading) return <div className="h-32 animate-pulse rounded-xl bg-slate-100" />
  const allowed = roles.some((role) => currentRoles.includes(role))
  if (!allowed) return <Navigate to="/forbidden" replace />
  return children
}
