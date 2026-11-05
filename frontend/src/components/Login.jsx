import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function Login() {
  const { login, error } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [localError, setLocalError] = useState('')

  async function onSubmit(e) {
    e.preventDefault()
    setBusy(true)
    setLocalError('')
    try {
      await login(email.trim(), password)
      const dest = location.state?.from && location.state.from !== '/login' ? location.state.from : '/overview'
      navigate(dest, { replace: true })
    } catch (err) {
      setLocalError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="brand" style={{ marginBottom: 8 }}>
          <div className="brand-mark">ML</div>
          <h1>MoMo Loop</h1>
        </div>
        <p className="login-sub">
          Sign in to access merchant acceptance intelligence for your assigned territory.
        </p>

        <form className="login-form" onSubmit={onSubmit}>
          <div className="field">
            <label htmlFor="email">Work email</label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {(localError || error) && <div className="login-error">{localError || error}</div>}
          <button className="btn-primary" type="submit" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
