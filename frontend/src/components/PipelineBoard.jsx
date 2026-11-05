import { useEffect, useMemo, useState } from 'react'
import { api, formatRand } from '../api'

const STATUSES = [
  { id: 'identified', label: 'Identified' },
  { id: 'reviewing', label: 'Under review' },
  { id: 'assigned', label: 'Assigned' },
  { id: 'onboarded', label: 'Onboarded' },
  { id: 'measured', label: 'Measured' },
]

const ACTION_LABELS = {
  'pipeline.created': 'Opportunity added',
  'pipeline.updated': 'Opportunity updated',
  'pipeline.deleted': 'Opportunity removed',
  'scenario.created': 'Scenario saved',
  'scenario.deleted': 'Scenario removed',
  'opportunities.exported': 'Report downloaded',
  'data.refreshed': 'Analytics refreshed',
  'data.uploaded': 'Dataset imported',
}

export default function PipelineBoard({ canEdit = false }) {
  const [items, setItems] = useState([])
  const [audit, setAudit] = useState([])
  const [assignees, setAssignees] = useState([])
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [notes, setNotes] = useState('')
  const [assignee, setAssignee] = useState('')
  const [status, setStatus] = useState('identified')
  const [saving, setSaving] = useState(false)

  async function refresh() {
    const jobs = [api.listPipeline(), api.listAudit(25)]
    if (canEdit) jobs.push(api.listAssignees())
    const [pipe, events, people] = await Promise.all(jobs)
    setItems(pipe)
    setAudit(events)
    if (people) setAssignees(people)
  }

  useEffect(() => {
    refresh()
      .catch((e) => setError(e.message))
  }, [canEdit])

  useEffect(() => {
    if (!selected) return
    setNotes(selected.notes || '')
    setAssignee(selected.assignee_name || '')
    setStatus(selected.status)
  }, [selected])

  const grouped = useMemo(() => {
    const map = Object.fromEntries(STATUSES.map((s) => [s.id, []]))
    for (const item of items) {
      if (!map[item.status]) map[item.status] = []
      map[item.status].push(item)
    }
    return map
  }, [items])

  async function saveSelected(e) {
    e.preventDefault()
    if (!selected || !canEdit) return
    setSaving(true)
    setMsg('')
    try {
      const updated = await api.updatePipeline(selected.id, {
        status,
        notes,
        assignee_name: assignee,
      })
      setSelected(updated)
      await refresh()
      setMsg('Opportunity updated successfully.')
    } catch (err) {
      setMsg(err.message)
    } finally {
      setSaving(false)
    }
  }

  async function removeSelected() {
    if (!selected || !canEdit) return
    if (!window.confirm('Remove this opportunity from the acquisition pipeline?')) return
    try {
      await api.deletePipeline(selected.id)
      setSelected(null)
      await refresh()
      setMsg('Opportunity removed from the pipeline.')
    } catch (err) {
      setMsg(err.message)
    }
  }

  if (error) return <div className="error">{error}</div>
  if (!items && !error) return <div className="loading">Loading acquisition pipeline…</div>

  return (
    <div className="panel">
      <div className="card" style={{ marginBottom: 14 }}>
        <h2>Acquisition pipeline</h2>
        <p className="sub">
          Track merchant acceptance opportunities from identification through onboarding and
          measurement.
          {canEdit ? '' : ' You currently have view-only access.'}
        </p>
        <div className="pipeline-board">
          {STATUSES.map((col) => (
            <div className="pipeline-col" key={col.id}>
              <div className="pipeline-col-head">
                <strong>{col.label}</strong>
                <span>{grouped[col.id]?.length || 0}</span>
              </div>
              <div className="pipeline-col-body">
                {(grouped[col.id] || []).map((item) => (
                  <button
                    type="button"
                    key={item.id}
                    className={`pipeline-card ${selected?.id === item.id ? 'active' : ''}`}
                    onClick={() => setSelected(item)}
                  >
                    <strong>
                      {item.location_name}
                    </strong>
                    <span className="tag">{item.merchant_category}</span>
                    <div className="pipeline-meta">
                      Score {item.opportunity_score.toFixed(0)} ·{' '}
                      {formatRand(item.estimated_recoverable)} recoverable
                    </div>
                  </button>
                ))}
                {(grouped[col.id] || []).length === 0 && (
                  <div className="pipeline-empty">None</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid-2 equal">
        <div className="card">
          <h2>Opportunity details</h2>
          {!selected ? (
            <p className="sub">Select an opportunity to review status, ownership and notes.</p>
          ) : (
            <>
              <p className="sub">
                {selected.location_name} · {selected.merchant_category}
                {selected.region ? ` · ${selected.region}` : ''}
              </p>
              <div className="sim-stats" style={{ marginTop: 0 }}>
                <div className="sim-stat">
                  <div className="label">Score</div>
                  <div className="value">{selected.opportunity_score.toFixed(1)}</div>
                </div>
                <div className="sim-stat">
                  <div className="label">Cash-out at risk</div>
                  <div className="value">{formatRand(selected.boundary_value)}</div>
                </div>
                <div className="sim-stat lift">
                  <div className="label">Recoverable value</div>
                  <div className="value">{formatRand(selected.estimated_recoverable)}</div>
                </div>
              </div>

              {canEdit ? (
                <form className="save-form" onSubmit={saveSelected}>
                  <div className="field">
                    <label>Status</label>
                    <select value={status} onChange={(e) => setStatus(e.target.value)}>
                      {STATUSES.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label>Owner</label>
                    <select value={assignee} onChange={(e) => setAssignee(e.target.value)}>
                      <option value="">Unassigned</option>
                      {assignees.map((a) => (
                        <option key={a.id} value={a.full_name}>
                          {a.full_name} · {a.role} · {a.region}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label>Notes</label>
                    <input
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="Rationale, next action or blockers"
                    />
                  </div>
                  <div className="row-actions">
                    <button className="btn-primary" type="submit" disabled={saving}>
                      {saving ? 'Saving…' : 'Save changes'}
                    </button>
                    <button type="button" className="btn-ghost danger" onClick={removeSelected}>
                      Remove
                    </button>
                  </div>
                  {msg && <div className="save-msg">{msg}</div>}
                </form>
              ) : (
                <>
                  <p className="sub">
                    Status: {STATUSES.find((s) => s.id === selected.status)?.label || selected.status}
                  </p>
                  <p className="sub">Owner: {selected.assignee_name || 'Unassigned'}</p>
                  <p className="sub">Notes: {selected.notes || 'None'}</p>
                </>
              )}
            </>
          )}
        </div>

        <div className="card">
          <h2>Activity log</h2>
          <p className="sub">Recent pipeline, scenario and data actions</p>
          {audit.length === 0 ? (
            <p className="sub">No recent activity.</p>
          ) : (
            <div className="audit-list">
              {audit.map((a) => (
                <div className="audit-item" key={a.id}>
                  <strong>{ACTION_LABELS[a.action] || a.action}</strong>
                  <span>{a.detail || 'No additional detail'}</span>
                  <span className="audit-meta">
                    {a.user_email || 'System'} · {new Date(a.created_at).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
