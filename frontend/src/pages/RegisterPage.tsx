import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError, registerAccount } from '../api'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import { Card } from '../components/ui/Card'
import { useToast } from '../components/Toast'

const REGISTERABLE_ROLES = ['Viewer', 'Sales', 'Engineer', 'Technician', 'QC', 'PM', 'Manager']

export default function RegisterPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [roleName, setRoleName] = useState('Viewer')
  const [error, setError] = useState('')
  const toast = useToast()

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')

    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    try {
      await registerAccount({ email, name, password, role_name: roleName || undefined })
      toast.push({ title: 'Account created', description: 'Please sign in with your new account.', variant: 'success' })
      navigate('/login')
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setError('Registration failed. Please verify your details and selected role.')
      } else {
        setError('Registration failed. Please try again.')
      }
      toast.push({ title: 'Registration failed', variant: 'error' })
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <Card className="w-full max-w-md p-6">
        <h1 className="text-xl font-semibold text-slate-900">Create Account</h1>
        <p className="mt-1 text-sm text-slate-500">Access AutoDev automation platform.</p>
        {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <div>
            <label className="text-sm" htmlFor="name">
              Name
            </label>
            <Input
              id="name"
              name="name"
              className="mt-1"
              autoComplete="name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
            />
          </div>
          <div>
            <label className="text-sm" htmlFor="email">
              Email
            </label>
            <Input
              id="email"
              name="email"
              type="email"
              className="mt-1"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>
          <div>
            <label className="text-sm" htmlFor="password">
              Password
            </label>
            <Input
              id="password"
              name="password"
              type="password"
              className="mt-1"
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>
          <div>
            <label className="text-sm" htmlFor="confirm-password">
              Confirm password
            </label>
            <Input
              id="confirm-password"
              name="confirmPassword"
              type="password"
              className="mt-1"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
            />
          </div>
          <div>
            <label className="text-sm" htmlFor="role-name">
              Role (optional)
            </label>
            <select
              id="role-name"
              name="role_name"
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm focus:border-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-200"
              value={roleName}
              onChange={(event) => setRoleName(event.target.value)}
            >
              {REGISTERABLE_ROLES.map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </select>
          </div>
          <Button className="w-full" type="submit">
            Create account
          </Button>
        </form>
        <div className="mt-4 text-sm text-slate-500">
          Already have an account?{' '}
          <Link className="text-blue-600" to="/login">
            Sign in
          </Link>
        </div>
      </Card>
    </div>
  )
}
