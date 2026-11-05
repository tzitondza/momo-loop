import { useEffect, useMemo, useState } from 'react'
import { NavLink, Navigate, Outlet, useLocation } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'

const ALL_TABS = [
  { id: 'overview', path: '/overview', label: 'Overview', permission: 'overview' },
  { id: 'boundaries', path: '/boundaries', label: 'Cash-out boundaries', permission: 'boundaries' },
  {
    id: 'opportunities',
    path: '/opportunities',
    label: 'Opportunities',
    permission: 'opportunities',
  },
  { id: 'pipeline', path: '/pipeline', label: 'Acquisition pipeline', permission: 'pipeline_view' },
  { id: 'simulate', path: '/simulate', label: 'Impact simulator', permission: 'simulate' },
  { id: 'users', path: '/users', label: 'Administration', permission: 'users' },
]

function formatRefreshed(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

export default function Layout() {
  const { user, can, logout } = useAuth()
  const location = useLocation()
  const [filters, setFilters] = useState(null)
  const [meta, setMeta] = useState(null)

  const tabs = useMemo(() => ALL_TABS.filter((t) => can(t.permission)), [user, can])

  useEffect(() => {
    if (!user) return
    api.meta().then(setMeta).catch(() => setMeta(null))
    if (!can('filters')) return
    api.filters().then(setFilters).catch(() => setFilters({ locations: [], categories: [] }))
  }, [user, can, location.pathname])

  if (!tabs.length) {
    return <div className="error">No modules are available for your role. Contact your administrator.</div>
  }

  const allowed = tabs.some((t) => location.pathname === t.path || location.pathname.startsWith(`${t.path}/`))
  if (location.pathname === '/' || !allowed) {
    return <Navigate to={tabs[0].path} replace />
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <div className="brand">
            <div className="brand-mark">ML</div>
            <h1>
              MoMo Loop <span>· Merchant Acceptance Intelligence</span>
            </h1>
          </div>
          <p className="tagline">
            Identify where wallet value exits into cash and prioritise merchant acceptance expansion
            that keeps more payments digital.
          </p>
        </div>
        <div className="badge-row user-bar">
          <span className="pill">MTN MoMo</span>
          <span className="pill soft">{user.full_name}</span>
          <button type="button" className="btn-ghost" onClick={logout}>
            Sign out
          </button>
        </div>
      </header>

      {meta?.last_refreshed && (
        <div className="meta-bar">
          Dataset updated {formatRefreshed(meta.last_refreshed)}
          {meta.national ? ' · National coverage' : ` · Regional coverage (${meta.region})`}
        </div>
      )}

      <nav className="nav-tabs">
        {tabs.map((t) => (
          <NavLink
            key={t.id}
            to={t.path}
            className={({ isActive }) => (isActive ? 'active' : undefined)}
          >
            {t.label}
          </NavLink>
        ))}
      </nav>

      <Outlet context={{ filters, meta, setMeta }} />
    </div>
  )
}
