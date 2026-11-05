import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { api, clearToken, getToken, setToken } from './api'

const AuthContext = createContext(null)

const ROLE_LABELS = {
  viewer: 'Viewer',
  analyst: 'Analyst',
  acquisition_lead: 'Acquisition Lead',
  admin: 'Administrator',
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [booting, setBooting] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const token = getToken()
    if (!token) {
      setBooting(false)
      return
    }
    api
      .me()
      .then(setUser)
      .catch(() => {
        clearToken()
        setUser(null)
      })
      .finally(() => setBooting(false))
  }, [])

  const value = useMemo(
    () => ({
      user,
      booting,
      error,
      roleLabel: user ? ROLE_LABELS[user.role] || user.role : '',
      can: (permission) => Boolean(user?.permissions?.includes(permission)),
      async login(email, password) {
        setError('')
        try {
          const res = await api.login(email, password)
          setToken(res.access_token)
          setUser(res.user)
          return res.user
        } catch (e) {
          setError(e.message || 'Login failed')
          throw e
        }
      },
      logout() {
        clearToken()
        setUser(null)
        setError('')
        if (window.location.pathname !== '/login') {
          window.location.assign('/login')
        }
      },
    }),
    [user, booting, error]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export { ROLE_LABELS }
