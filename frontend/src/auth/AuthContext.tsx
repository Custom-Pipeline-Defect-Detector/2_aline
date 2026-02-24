import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { ApiError, getMe } from '../api'
import type { Permission, Role } from './permissions'
import { PERMISSIONS } from './permissions'

type AuthState = {
  user: any | null
  roles: Role[]
  loading: boolean
  hasRole: (role: Role) => boolean
  can: (permission: Permission) => boolean
  logout: () => void
}

const AuthContext = createContext<AuthState>({
  user: null,
  roles: [],
  loading: true,
  hasRole: () => false,
  can: () => false,
  logout: () => {},
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<any | null>(null)
  const [roles, setRoles] = useState<Role[]>([])
  const [loading, setLoading] = useState(true)

  const loadUser = async () => {
    try {
      const token = localStorage.getItem('token')
      if (!token) {
        setUser(null)
        setRoles([])
        setLoading(false)
        return
      }

      const me = await getMe()
      const nextRoles = (me?.roles || []).map((r: any) => r.name as Role)

      setUser(me)
      setRoles(nextRoles)
    } catch (error) {
      // if unauthorized or any error, fail closed
      setUser(null)
      setRoles([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // load on first mount
    void loadUser()
  }, [])

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
    setRoles([])
    setLoading(false)
  }

  const value = useMemo(
    () => ({
      user,
      roles,
      loading,
      logout,
      hasRole: (role: Role) => roles.includes(role),
      can: (permission: Permission) => {
        const allowed = PERMISSIONS[permission]
        if (!allowed) return false
        return allowed.some((role) => roles.includes(role))
      },
    }),
    [loading, roles, user]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
