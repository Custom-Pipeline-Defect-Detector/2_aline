import { useAuth } from '../auth/AuthContext'
import { PERMISSIONS } from '../auth/permissions'

export default function PermissionDebugPanel() {
  const { roles, can } = useAuth()
  if (!import.meta.env.DEV) return null
  return (
    <div className="mt-4 rounded-lg border border-dashed border-slate-300 bg-white p-3 text-xs text-slate-600">
      <div className="font-semibold">Permissions debug</div>
      <div>Roles: {roles.join(', ') || 'none'}</div>
      {Object.keys(PERMISSIONS).map((key) => (
        <div key={key}>{key}: {can(key as any) ? '✅' : '❌'}</div>
      ))}
    </div>
  )
}
