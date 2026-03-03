const envApiBase = import.meta.env.VITE_API_BASE_URL
const API_BASE = envApiBase ? envApiBase.replace(/\/+$/, '') : ''
const BASE_HAS_API = API_BASE.endsWith('/api')

export const buildApiUrl = (path: string) => {
  const trimmed = path.startsWith('/') ? path : `/${path}`
  const withPrefix = trimmed.startsWith('/api') || BASE_HAS_API ? trimmed : `/api${trimmed}`
  return `${API_BASE}${withPrefix}`
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export function getToken() {
  return localStorage.getItem('token')
}

export async function apiFetch(path: string, options: RequestInit = {}) {
  const token = getToken()
  const headers = new Headers(options.headers || {})
  const method = String(options.method || 'GET').toUpperCase()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const response = await fetch(buildApiUrl(path), {
    ...options,
    headers,
    cache: options.cache ?? (method === 'GET' ? 'no-store' : 'default'),
  })
  if (!response.ok) {
    const text = await response.text()
    let message = text || response.statusText
    if (text) {
      try {
        const parsed = JSON.parse(text) as { detail?: unknown }
        if (typeof parsed.detail === 'string') {
          message = parsed.detail
        } else if (Array.isArray(parsed.detail)) {
          message = parsed.detail
            .map((item) => {
              if (typeof item === 'string') return item
              if (item && typeof item === 'object' && 'msg' in item) return String((item as { msg?: unknown }).msg)
              return JSON.stringify(item)
            })
            .join('; ')
        }
      } catch {
        // keep raw text fallback
      }
    }
    if (response.status === 401) {
      localStorage.removeItem('token')
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.assign('/login')
      }
    }
    throw new ApiError(response.status, message)
  }
  if (response.status === 204) return null
  try {
    return await response.json()
  } catch {
    return null
  }
}

export async function login(username: string, password: string) {
  const body = new URLSearchParams()
  body.set('username', username)
  body.set('password', password)
  const response = await fetch(buildApiUrl('/auth/login'), {
    method: 'POST',
    body,
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  if (!response.ok) {
    const message = await response.text()
    throw new ApiError(response.status, message || 'Login failed')
  }
  return response.json()
}

export async function loginAndValidate(username: string, password: string) {
  const data = await login(username, password)
  if (!data?.access_token) {
    throw new Error('Login response missing access token')
  }
  localStorage.setItem('token', data.access_token)
  if (data.token_type) {
    localStorage.setItem('token_type', data.token_type)
  }
  await apiFetch('/auth/me')
  return data
}

export async function getMe() {
  return apiFetch('/auth/me')
}

export async function registerAccount(payload: { name: string; email: string; password: string; role_name?: string }) {
  return apiFetch('/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function fetchNotifications(unreadOnly = false) {
  return apiFetch(`/notifications?unread_only=${unreadOnly}`)
}

export async function markNotificationRead(id: number) {
  return apiFetch(`/notifications/${id}/read`, { method: 'POST' })
}

export async function markAllNotificationsRead() {
  return apiFetch('/notifications/read_all', { method: 'POST' })
}

export async function reprocessDocument(id: number) {
  return apiFetch(`/documents/${id}/reprocess`, { method: 'POST' })
}
