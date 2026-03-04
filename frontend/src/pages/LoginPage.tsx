import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError, loginAndValidate } from '../api'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import { Card } from '../components/ui/Card'
import { useToast } from '../components/Toast'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const toast = useToast()

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    try {
      await loginAndValidate(email, password)
      toast.push({ title: 'Welcome back', description: 'Login successful.', variant: 'success' })
      navigate('/dashboard')
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError('Invalid email or password.')
        toast.push({ title: 'Login failed', description: 'Invalid email or password.', variant: 'error' })
        return
      }
      setError('Unable to sign in right now. Please check your network and try again.')
      toast.push({ title: 'Login unavailable', description: 'Could not reach the server.', variant: 'error' })
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <Card className="w-full max-w-md p-6">
        <h1 className="text-xl font-semibold text-slate-900">Login</h1>
        <p className="mt-1 text-sm text-slate-500">Access AutoDev automation platform.</p>
        {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <div>
            <label className="text-sm" htmlFor="email">
              Email
            </label>
            <Input
              id="email"
              name="email"
              className="mt-1"
              type="email"
              autoComplete="username"
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
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>
          <Button className="w-full" type="submit">
            Sign in
          </Button>
        </form>
        <div className="mt-4 text-center text-sm text-slate-600">
          Don&apos;t have an account?{' '}
          <Link to="/register" className="font-medium text-blue-600 hover:text-blue-700">
            Register account
          </Link>
        </div>
      </Card>
    </div>
  )
}
