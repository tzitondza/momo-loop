import { Navigate, Route, Routes, useOutletContext } from 'react-router-dom'
import { useAuth } from './auth'
import Login from './components/Login'
import Layout from './components/Layout'
import RequireAuth from './components/RequireAuth'
import Overview from './components/Overview'
import BoundaryExplorer from './components/BoundaryExplorer'
import OpportunityRanking from './components/OpportunityRanking'
import ImpactSimulator from './components/ImpactSimulator'
import UsersPanel from './components/UsersPanel'
import PipelineBoard from './components/PipelineBoard'

function BoundariesPage() {
  const { filters } = useOutletContext()
  return <BoundaryExplorer filters={filters} />
}

function SimulatePage() {
  const { filters } = useOutletContext()
  const { can } = useAuth()
  return <ImpactSimulator filters={filters} canSave={can('scenarios')} />
}

function PipelinePage() {
  const { can } = useAuth()
  return <PipelineBoard canEdit={can('pipeline')} />
}

function UsersPage() {
  const { setMeta } = useOutletContext()
  return <UsersPanel onRefreshed={setMeta} />
}

export default function App() {
  const { user, booting } = useAuth()

  if (booting) {
    return <div className="loading">Loading MoMo Loop…</div>
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to="/overview" replace /> : <Login />}
      />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/overview" replace />} />
        <Route path="overview" element={<Overview />} />
        <Route path="boundaries" element={<BoundariesPage />} />
        <Route path="opportunities" element={<OpportunityRanking />} />
        <Route path="pipeline" element={<PipelinePage />} />
        <Route path="simulate" element={<SimulatePage />} />
        <Route path="users" element={<UsersPage />} />
      </Route>
      <Route path="*" element={<Navigate to={user ? '/overview' : '/login'} replace />} />
    </Routes>
  )
}
