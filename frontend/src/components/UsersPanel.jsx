import { useEffect, useState } from 'react'
import { api } from '../api'
import { ROLE_LABELS, useAuth } from '../auth'

const DATASETS = [
  {
    id: 'transactions',
    label: 'Transactions',
    hint: 'Required fields: transaction ID, customer ID, type, amount, timestamp, location ID',
  },
  {
    id: 'merchants',
    label: 'Merchants',
    hint: 'Required fields: merchant ID, name, location ID, category, MoMo acceptance status',
  },
  {
    id: 'locations',
    label: 'Locations',
    hint: 'Required fields: location ID, name, region, latitude, longitude',
  },
]

export default function UsersPanel({ onRefreshed }) {
  const { can } = useAuth()
  const [users, setUsers] = useState([])
  const [config, setConfig] = useState(null)
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const [dataset, setDataset] = useState('transactions')
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)

  async function load() {
    const jobs = [api.listUsers()]
    if (can('config')) jobs.push(api.getConfig())
    const [userRows, cfg] = await Promise.all(jobs)
    setUsers(userRows)
    if (cfg) setConfig(cfg)
  }

  useEffect(() => {
    load().catch((e) => setError(e.message))
  }, [])

  function bumpMeta(lastRefreshed) {
    if (!onRefreshed) return
    onRefreshed({
      region: config?.scope?.region || 'South Africa',
      national: true,
      last_refreshed: lastRefreshed,
    })
  }

  async function refreshData() {
    setRefreshing(true)
    setMsg('')
    try {
      const result = await api.refreshData()
      setMsg(
        `Analytics refreshed successfully · ${result.transaction_count.toLocaleString()} transactions · updated ${new Date(
          result.last_refreshed
        ).toLocaleString()}`
      )
      bumpMeta(result.last_refreshed)
      const cfg = await api.getConfig()
      setConfig(cfg)
    } catch (err) {
      setMsg(err.message)
    } finally {
      setRefreshing(false)
    }
  }

  async function uploadCsv(e) {
    e.preventDefault()
    if (!file) {
      setMsg('Please select a CSV file to continue.')
      return
    }
    setUploading(true)
    setMsg('')
    try {
      const result = await api.uploadDataset(dataset, file)
      setMsg(
        `${DATASETS.find((d) => d.id === result.dataset)?.label || 'Dataset'} imported successfully · ${result.rows.toLocaleString()} records processed.`
      )
      setFile(null)
      bumpMeta(result.last_refreshed)
      const cfg = await api.getConfig()
      setConfig(cfg)
    } catch (err) {
      setMsg(err.message)
    } finally {
      setUploading(false)
    }
  }

  if (error) return <div className="error">{error}</div>
  if (!users.length && !error) return <div className="loading">Loading administration…</div>

  const selectedMeta = DATASETS.find((d) => d.id === dataset)

  return (
    <div className="panel">
      {can('config') && (
        <>
          <div className="card" style={{ marginBottom: 14 }}>
            <h2>Platform configuration</h2>
            <p className="sub">
              Review system status and refresh analytics after source data has been updated.
            </p>
            <div className="sim-stats">
              <div className="sim-stat">
                <div className="label">Platform version</div>
                <div className="value" style={{ fontSize: '1rem' }}>
                  {config?.version || '—'}
                </div>
              </div>
              <div className="sim-stat">
                <div className="label">Authentication</div>
                <div className="value" style={{ fontSize: '1rem' }}>
                  Secure sign-in
                </div>
              </div>
              <div className="sim-stat">
                <div className="label">Dataset updated</div>
                <div className="value" style={{ fontSize: '0.95rem' }}>
                  {config?.scope?.last_refreshed
                    ? new Date(config.scope.last_refreshed).toLocaleString()
                    : '—'}
                </div>
              </div>
            </div>
            <div className="row-actions" style={{ marginTop: 8 }}>
              <button type="button" className="btn-primary" onClick={refreshData} disabled={refreshing}>
                {refreshing ? 'Refreshing…' : 'Refresh analytics'}
              </button>
            </div>
          </div>

          <div className="card" style={{ marginBottom: 14 }}>
            <h2>Import anonymised data</h2>
            <p className="sub">
              Upload a validated CSV batch to replace the selected dataset. The previous version is
              retained securely for rollback.
            </p>
            <form className="save-form" onSubmit={uploadCsv}>
              <div className="field">
                <label>Dataset type</label>
                <select value={dataset} onChange={(e) => setDataset(e.target.value)}>
                  {DATASETS.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>CSV file</label>
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
              </div>
              <p className="sub">{selectedMeta?.hint}</p>
              <button className="btn-primary" type="submit" disabled={uploading}>
                {uploading ? 'Importing…' : 'Import dataset'}
              </button>
            </form>
            {msg && <div className="save-msg" style={{ marginTop: 10 }}>{msg}</div>}
          </div>
        </>
      )}

      <div className="card">
        <h2>User access</h2>
        <p className="sub">Workspace accounts, roles and territorial scope.</p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Territory</th>
                <th>Access</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.full_name}</td>
                  <td>{u.email}</td>
                  <td>
                    <span className="tag">{ROLE_LABELS[u.role] || u.role}</span>
                  </td>
                  <td>{u.region}</td>
                  <td style={{ whiteSpace: 'normal', maxWidth: 320 }}>
                    {u.permissions.join(', ')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
