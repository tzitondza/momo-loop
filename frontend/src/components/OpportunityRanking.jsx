import { useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api, formatRand, formatPct } from '../api'
import { useAuth } from '../auth'

export default function OpportunityRanking() {
  const { can } = useAuth()
  const [data, setData] = useState(null)
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [adding, setAdding] = useState(false)
  const [exporting, setExporting] = useState(false)
  const canPipeline = can('pipeline')

  useEffect(() => {
    api
      .opportunities(20)
      .then((d) => {
        setData(d)
        setSelected(d.opportunities[0] || null)
      })
      .catch((e) => setError(e.message))
  }, [])

  async function exportReport(format) {
    setExporting(true)
    setMsg('')
    try {
      await api.exportOpportunities(100, format)
      setMsg(`${format.toUpperCase()} download started.`)
    } catch (err) {
      setMsg(err.message)
    } finally {
      setExporting(false)
    }
  }

  async function addToPipeline() {
    if (!selected || !canPipeline) return
    setAdding(true)
    setMsg('')
    try {
      await api.createPipeline({
        location_id: selected.location_id,
        location_name: selected.location_name,
        region: selected.region || '',
        merchant_category: selected.merchant_category,
        opportunity_score: selected.opportunity_score,
        boundary_value: selected.boundary_value,
        estimated_recoverable: selected.estimated_recoverable,
        affected_customers: selected.affected_customers,
        notes: selected.reasons?.slice(0, 2).join(' · ') || '',
      })
      setMsg('Opportunity added to the acquisition pipeline.')
    } catch (err) {
      setMsg(err.message)
    } finally {
      setAdding(false)
    }
  }

  if (error) return <div className="error">{error}</div>
  if (!data) return <div className="loading">Loading opportunity ranking…</div>

  const chart = data.opportunities.slice(0, 10).map((o) => ({
    name: `${o.location_name.split(' ')[0]} · ${o.merchant_category}`,
    score: o.opportunity_score,
    recoverable: o.estimated_recoverable,
  }))

  return (
    <div className="panel">
      <div className="grid-2">
        <div className="card">
          <div className="card-head-row">
            <div>
              <h2>Ranked opportunities</h2>
              <p className="sub">
                Prioritised by recoverable value, customers affected, cash-out frequency, acceptance
                gap and onboarding feasibility.
                {data.scope?.region ? ` Territory: ${data.scope.region}.` : ''}
              </p>
            </div>
            <div>
              <div className="row-actions">
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => exportReport('csv')}
                  disabled={exporting}
                >
                  {exporting ? 'Preparing…' : 'Download CSV'}
                </button>
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => exportReport('pdf')}
                  disabled={exporting}
                >
                  Download PDF
                </button>
              </div>
              {msg && <div className="save-msg" style={{ marginTop: 8 }}>{msg}</div>}
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Opportunity</th>
                  <th>Score</th>
                  <th>Cash-out at risk</th>
                  <th>Gap</th>
                  <th>Recoverable</th>
                </tr>
              </thead>
              <tbody>
                {data.opportunities.map((o) => (
                  <tr
                    key={`${o.location_id}-${o.merchant_category}`}
                    onClick={() => {
                      setSelected(o)
                      setMsg('')
                    }}
                    style={{
                      cursor: 'pointer',
                      background:
                        selected?.location_id === o.location_id &&
                        selected?.merchant_category === o.merchant_category
                          ? 'rgba(255,204,0,0.14)'
                          : undefined,
                    }}
                  >
                    <td>
                      <span className="rank">{o.rank}</span>
                    </td>
                    <td>
                      <strong>{o.location_name}</strong>
                      <div style={{ display: 'flex', gap: 6, marginTop: 4, alignItems: 'center' }}>
                        <span className="tag">{o.merchant_category}</span>
                        {o.is_planted_gap && <span className="tag gap">Priority gap</span>}
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        {o.opportunity_score}
                        <div className="score-bar">
                          <span style={{ width: `${o.opportunity_score}%` }} />
                        </div>
                      </div>
                    </td>
                    <td>{formatRand(o.boundary_value)}</td>
                    <td>{formatPct(o.acceptance_gap, 0)}</td>
                    <td>{formatRand(o.estimated_recoverable)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <h2>Top priorities</h2>
          <p className="sub">Highest-scoring locations and merchant categories for expansion</p>
          <div style={{ width: '100%', height: 280 }}>
            <ResponsiveContainer>
              <BarChart data={chart} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="score" fill="#ffcc00" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {selected && (
            <>
              <h2 style={{ marginTop: 16 }}>
                Recommendation #{selected.rank}: {selected.location_name} ·{' '}
                {selected.merchant_category}
              </h2>
              <ul className="reason-list">
                {selected.reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
              {canPipeline && (
                <div style={{ marginTop: 14 }}>
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={addToPipeline}
                    disabled={adding}
                  >
                    {adding ? 'Adding…' : 'Add to pipeline'}
                  </button>
                </div>
              )}
            </>
          )}

          <div className="disclaimer">
            Validation hit rate against known acceptance gaps:{' '}
            <strong>{formatPct(data.scoring.ranking_quality_vs_planted_gaps, 0)}</strong>.{' '}
            {data.scoring.note}
          </div>
        </div>
      </div>
    </div>
  )
}
