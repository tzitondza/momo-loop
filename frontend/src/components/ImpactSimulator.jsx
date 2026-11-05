import { useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api, formatRand } from '../api'

export default function ImpactSimulator({ filters, canSave = false }) {
  const [locationId, setLocationId] = useState('')
  const [category, setCategory] = useState('')
  const [recoveryRate, setRecoveryRate] = useState(0.35)
  const [merchants, setMerchants] = useState(5)
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [scenarios, setScenarios] = useState([])
  const [scenarioName, setScenarioName] = useState('')
  const [scenarioNotes, setScenarioNotes] = useState('')
  const [saveMsg, setSaveMsg] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => {
      api
        .simulate({
          location_id: locationId || undefined,
          category: category || undefined,
          recovery_rate: recoveryRate,
          merchants_to_onboard: merchants,
        })
        .then((res) => {
          setData(res)
          setError('')
        })
        .catch((e) => setError(e.message))
    }, 120)
    return () => clearTimeout(t)
  }, [locationId, category, recoveryRate, merchants])

  useEffect(() => {
    if (!canSave) return
    api
      .listScenarios()
      .then(setScenarios)
      .catch(() => setScenarios([]))
  }, [canSave])

  async function refreshScenarios() {
    const rows = await api.listScenarios()
    setScenarios(rows)
  }

  async function saveScenario(e) {
    e.preventDefault()
    if (!scenarioName.trim()) {
      setSaveMsg('Please enter a scenario name.')
      return
    }
    setSaving(true)
    setSaveMsg('')
    try {
      await api.createScenario({
        name: scenarioName.trim(),
        notes: scenarioNotes.trim(),
        location_id: locationId || null,
        category: category || null,
        recovery_rate: recoveryRate,
        merchants_to_onboard: merchants,
      })
      setScenarioName('')
      setScenarioNotes('')
      setSaveMsg('Scenario saved successfully.')
      await refreshScenarios()
    } catch (err) {
      setSaveMsg(err.message)
    } finally {
      setSaving(false)
    }
  }

  function loadScenario(s) {
    setLocationId(s.location_id || '')
    setCategory(s.category || '')
    setRecoveryRate(s.recovery_rate)
    setMerchants(s.merchants_to_onboard)
    setSaveMsg(`Scenario “${s.name}” loaded.`)
  }

  async function removeScenario(id) {
    try {
      await api.deleteScenario(id)
      await refreshScenarios()
      setSaveMsg('Scenario removed.')
    } catch (err) {
      setSaveMsg(err.message)
    }
  }

  if (error) return <div className="error">{error}</div>
  if (!data) return <div className="loading">Calculating impact…</div>

  if (data.error) {
    return (
      <div className="panel">
        <div className="card">
          <p>{data.error}</p>
        </div>
      </div>
    )
  }

  const chart = [
    {
      metric: 'Cash-out at risk',
      Baseline: data.baseline.boundary_cash_out_value,
      Projected: data.projected.boundary_cash_out_value,
    },
    {
      metric: 'Merchant payments',
      Baseline: data.baseline.digital_merchant_payments,
      Projected: data.projected.digital_merchant_payments,
    },
  ]

  const locationName =
    filters?.locations?.find((l) => l.location_id === locationId)?.name || 'All locations'

  return (
    <div className="panel">
      <div className="card">
        <h2>Impact simulator</h2>
        <p className="sub">
          Model the effect of expanding merchant acceptance under different recovery assumptions.
        </p>

        <div className="toolbar">
          <div className="field">
            <label>Location</label>
            <select value={locationId} onChange={(e) => setLocationId(e.target.value)}>
              <option value="">All locations</option>
              {(filters?.locations || []).map((l) => (
                <option key={l.location_id} value={l.location_id}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Merchant category</label>
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">All categories</option>
              {(filters?.categories || []).map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div className="field" style={{ minWidth: 220 }}>
            <label>Recovery rate · {(recoveryRate * 100).toFixed(0)}%</label>
            <input
              type="range"
              min="0.1"
              max="0.7"
              step="0.05"
              value={recoveryRate}
              onChange={(e) => setRecoveryRate(Number(e.target.value))}
            />
          </div>
          <div className="field" style={{ minWidth: 220 }}>
            <label>Merchants to onboard · {merchants}</label>
            <input
              type="range"
              min="1"
              max="20"
              step="1"
              value={merchants}
              onChange={(e) => setMerchants(Number(e.target.value))}
            />
          </div>
        </div>

        <div className="sim-stats">
          <div className="sim-stat">
            <div className="label">Current cash-out at risk</div>
            <div className="value">{formatRand(data.baseline.boundary_cash_out_value)}</div>
          </div>
          <div className="sim-stat lift">
            <div className="label">Projected value retained</div>
            <div className="value">{formatRand(data.projected.value_retained)}</div>
          </div>
          <div className="sim-stat">
            <div className="label">Merchant payment uplift</div>
            <div className="value">+{data.projected.retention_lift_pct}%</div>
          </div>
        </div>

        <div className="grid-2 equal">
          <div style={{ width: '100%', height: 280 }}>
            <ResponsiveContainer>
              <BarChart data={chart}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                <XAxis dataKey="metric" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
                <Tooltip formatter={(v) => formatRand(v)} />
                <Legend />
                <Bar dataKey="Baseline" fill="#2c2c2c" radius={[6, 6, 0, 0]} />
                <Bar dataKey="Projected" fill="#ffcc00" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div>
            <h2>Recommended targets</h2>
            <p className="sub">Highest-priority merchant categories within the selected filters</p>
            <div className="table-wrap" style={{ maxHeight: 240 }}>
              <table>
                <thead>
                  <tr>
                    <th>Location</th>
                    <th>Category</th>
                    <th>Score</th>
                    <th>Boundary</th>
                  </tr>
                </thead>
                <tbody>
                  {data.priority_targets.map((t) => (
                    <tr key={`${t.location_name}-${t.merchant_category}`}>
                      <td>{t.location_name}</td>
                      <td>
                        <span className="tag">{t.merchant_category}</span>
                      </td>
                      <td>{t.score}</td>
                      <td>{formatRand(t.boundary_value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="disclaimer">
              <strong>Assumptions:</strong>
              <ul className="reason-list">
                {data.assumptions.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>

      {canSave && (
        <div className="grid-2 equal" style={{ marginTop: 14 }}>
          <div className="card">
            <h2>Save scenario</h2>
            <p className="sub">
              Store the current assumptions for {locationName}
              {category ? ` · ${category}` : ''} for later review by the acquisition team.
            </p>
            <form className="save-form" onSubmit={saveScenario}>
              <div className="field">
                <label>Scenario name</label>
                <input
                  value={scenarioName}
                  onChange={(e) => setScenarioName(e.target.value)}
                  placeholder="e.g. Alexandra grocery expansion"
                />
              </div>
              <div className="field">
                <label>Notes</label>
                <input
                  value={scenarioNotes}
                  onChange={(e) => setScenarioNotes(e.target.value)}
                  placeholder="Business rationale or next actions"
                />
              </div>
              <button className="btn-primary" type="submit" disabled={saving}>
                {saving ? 'Saving…' : 'Save scenario'}
              </button>
              {saveMsg && <div className="save-msg">{saveMsg}</div>}
            </form>
          </div>

          <div className="card">
            <h2>Saved scenarios</h2>
            <p className="sub">Reopen a previous simulation or remove scenarios that are no longer relevant.</p>
            {scenarios.length === 0 ? (
              <p className="sub">No saved scenarios yet.</p>
            ) : (
              <div className="table-wrap" style={{ maxHeight: 280 }}>
                <table>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Retained</th>
                      <th>Lift</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {scenarios.map((s) => (
                      <tr key={s.id}>
                        <td>
                          <strong>{s.name}</strong>
                          <div style={{ color: '#6b6b6b', fontSize: '0.75rem' }}>
                            {(s.location_id || 'All') + (s.category ? ` · ${s.category}` : '')}
                          </div>
                        </td>
                        <td>{formatRand(s.projected_value_retained)}</td>
                        <td>+{s.retention_lift_pct}%</td>
                        <td>
                          <div className="row-actions">
                            <button type="button" className="btn-ghost" onClick={() => loadScenario(s)}>
                              Load
                            </button>
                            <button
                              type="button"
                              className="btn-ghost danger"
                              onClick={() => removeScenario(s.id)}
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {!canSave && (
        <div className="disclaimer" style={{ marginTop: 14 }}>
          Your role can run simulations. Saving scenarios requires Acquisition Lead or Administrator
          access.
        </div>
      )}
    </div>
  )
}
