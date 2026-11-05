import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import { api, formatRand } from '../api'

export default function BoundaryExplorer({ filters }) {
  const [locationId, setLocationId] = useState('')
  const [category, setCategory] = useState('')
  const [data, setData] = useState(null)
  const [mapData, setMapData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .boundaries({ location_id: locationId || undefined, category: category || undefined })
      .then(setData)
      .catch((e) => setError(e.message))
  }, [locationId, category])

  useEffect(() => {
    api.map().then(setMapData).catch(() => {})
  }, [])

  if (error) return <div className="error">{error}</div>
  if (!data) return <div className="loading">Loading cash-out boundaries…</div>

  const maxVal = Math.max(...(mapData?.points?.map((p) => p.boundary_value) || [1]), 1)

  return (
    <div className="panel">
      <div className="toolbar">
        <div className="field">
          <label>Location</label>
          <select value={locationId} onChange={(e) => setLocationId(e.target.value)}>
            <option value="">All locations</option>
            {(filters?.locations || []).map((l) => (
              <option key={l.location_id} value={l.location_id}>
                {l.name} ({l.region})
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
        <div className="pill soft">
          Detection window: {data.window_minutes} min · {data.total_boundaries.toLocaleString()}{' '}
          events · {formatRand(data.total_boundary_value)}
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <h2>Priority hotspots</h2>
          <p className="sub">
            Locations and categories where wallet inflows are frequently followed by cash-out within{' '}
            {data.window_minutes} minutes.
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Location</th>
                  <th>Category</th>
                  <th>Events</th>
                  <th>Value</th>
                  <th>Customers</th>
                  <th>Acceptance</th>
                </tr>
              </thead>
              <tbody>
                {data.hotspots.map((h) => (
                  <tr key={`${h.location_id}-${h.merchant_category}`}>
                    <td>
                      {h.location_name}
                      <div style={{ color: '#6b6b6b', fontSize: '0.75rem' }}>{h.region}</div>
                    </td>
                    <td>
                      <span className="tag">{h.merchant_category}</span>
                    </td>
                    <td>{h.boundary_count}</td>
                    <td>{formatRand(h.boundary_value)}</td>
                    <td>{h.affected_customers}</td>
                    <td>{(h.merchant_acceptance_rate * 100).toFixed(0)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="disclaimer">{data.disclaimer}</div>
        </div>

        <div className="card">
          <h2>Geographic view</h2>
          <p className="sub">Marker size reflects cash-out value associated with each location.</p>
          <div className="map-wrap">
            {mapData && (
              <MapContainer center={[-28.5, 25.0]} zoom={5} scrollWheelZoom={false}>
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                {mapData.points.map((p) => (
                  <CircleMarker
                    key={p.location_id}
                    center={[p.lat, p.lng]}
                    radius={8 + (p.boundary_value / maxVal) * 22}
                    pathOptions={{
                      color: '#0b0b0b',
                      fillColor: '#ffcc00',
                      fillOpacity: 0.65,
                      weight: 1,
                    }}
                  >
                    <Popup>
                      <strong>{p.name}</strong>
                      <br />
                      {p.region}
                      <br />
                      Cash-out at risk: {formatRand(p.boundary_value)}
                      <br />
                      Priority score: {p.top_score}
                    </Popup>
                  </CircleMarker>
                ))}
              </MapContainer>
            )}
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <h2>Customer journey examples</h2>
        <p className="sub">Selected inflow-to-cash-out sequences, ordered by cash-out value</p>
        <div className="journey-list">
          {data.journeys.map((j) => (
            <div className="journey" key={j.cashout_id}>
              <div className="journey-flow">
                <span className="flow-node in">
                  {j.inflow_type || 'Inflow'} {formatRand(j.inflow_amount)}
                </span>
                <span className="flow-arrow">→ {j.minutes_after_inflow} min →</span>
                <span className="flow-node out">Cash-out {formatRand(j.cashout_amount)}</span>
              </div>
              <div className="meta">
                <span>{j.customer_id}</span>
                <span>{j.location_name}</span>
                <span>{j.merchant_category || 'Category not specified'}</span>
                <span>{j.timestamp}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
