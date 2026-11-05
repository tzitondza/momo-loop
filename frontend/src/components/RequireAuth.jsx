import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth'

export default function RequireAuth({ children }) {
  const { user, booting } = useAuth()
  const location = useLocation()

  if (booting) {
    return <div className="loading">Loading MoMo Loop…</div>
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return children
}
