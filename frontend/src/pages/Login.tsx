import React, { useState } from 'react'
import { apiPost } from '../app/api'

export default function Login() {
  const [email, setEmail] = useState('admin@aline.local')
  const [password, setPassword] = useState('Admin123!')
  const [err, setErr] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setErr(null)

    try {
      const res = await apiPost('/auth/login', { email, password })
      localStorage.setItem('token', res.token)

      // ✅ Force full reload so AuthContext re-fetches /me for the new user
      window.location.href = '/dashboard' // or '/inbox' if you prefer
    } catch (e: any) {
      setErr(String(e))
    }
  }

  return (
    <div className="max-w-md mx-auto mt-10 border rounded p-6">
      <div className="text-xl font-semibold mb-4">Login</div>
      {err && <div className="text-red-700 text-sm mb-2">{err}</div>}

      <form onSubmit={submit} className="flex flex-col gap-3">
        <label className="text-sm">Email</label>
        <input
          className="border p-2 rounded"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <label className="text-sm">Password</label>
        <input
          className="border p-2 rounded"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <button className="mt-2 bg-blue-700 text-white p-2 rounded">Login</button>
      </form>

      <div className="text-xs text-gray-600 mt-3">
        Seeded admin: admin@aline.local / Admin123!
      </div>
    </div>
  )
}
