import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { getToken } from '../api'

export default function RequireAuth() {
  const location = useLocation()
  const token = getToken()

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return <Outlet />
}
