import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError, registerAccount } from '../api'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import { Card } from '../components/ui/Card'
import { useToast } from '../components/Toast'

const REGISTERABLE_ROLES = ['Viewer', 'Sales', 'Engineer', 'Technician', 'QC', 'PM', 'Manager']

const ENGINEER_TYPES = [
  'plc_engineer',
  'software_engineer', 
  'mechanical_engineer',
  'electrical_engineer',
  'hardware_engineer',
  'design_3d_engineer'
];

const ENGINEER_LEVELS = ['lead', 'normal'];

export default function RegisterPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [roleName, setRoleName] = useState('Viewer')
  const [engineerType, setEngineerType] = useState('')
  const [engineerLevel, setEngineerLevel] = useState('')
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
      const registrationData: any = { email, name, password, role_name: roleName || undefined };
      
      // Add engineer-specific fields if role is Engineer
      if (roleName === 'Engineer') {
        if (!engineerType || !engineerLevel) {
          setError('Please select both engineer type and level.');
          return;
        }
        registrationData.engineer_type = engineerType;
        registrationData.engineer_level = engineerLevel;
      }
      
      await registerAccount(registrationData);
      toast.push({ title: 'Account created', description: 'Please sign in with your new account.', variant: 'success' });
      navigate('/login');
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setError('Registration failed. Please verify your details and selected role.');
      } else {
        setError('Registration failed. Please try again.');
      }
      toast.push({ title: 'Registration failed', variant: 'error' });
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
          
          {/* Show engineer-specific fields when role is Engineer */}
          {roleName === 'Engineer' && (
            <>
              <div>
                <label className="text-sm" htmlFor="engineer-type">
                  Engineer Type
                </label>
                <select
                  id="engineer-type"
                  className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm focus:border-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  value={engineerType}
                  onChange={(event) => setEngineerType(event.target.value)}
                  required
                >
                  <option value="">Select engineer type</option>
                  {ENGINEER_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="text-sm" htmlFor="engineer-level">
                  Engineer Level
                </label>
                <select
                  id="engineer-level"
                  className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm focus:border-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  value={engineerLevel}
                  onChange={(event) => setEngineerLevel(event.target.value)}
                  required
                >
                  <option value="">Select engineer level</option>
                  {ENGINEER_LEVELS.map((level) => (
                    <option key={level} value={level}>
                      {level.charAt(0).toUpperCase() + level.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
            </>
          )}
          
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


