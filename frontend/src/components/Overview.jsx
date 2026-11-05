import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api, formatRand, formatPct } from '../api'
import { useEffect, useState } from 'react'

export default function Overview() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.overview().then(setData).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="error">{error}</div>
  if (!data) return <div className="loading">Loading overview…</div>

  const { kpis, trend, disclaimer, scope } = data
  const chartData = trend.map((d) => ({
    day: d.day.slice(5),
    'Cash-out': d['cash-out'] || 0,
    'Merchant payment': d['merchant payment'] || 0,
    P2P: d.P2P || 0,
  }))

  const cards = [
    {
      label: 'Total transaction value',
      value: formatRand(kpis.total_transaction_value),
      hint: `${kpis.transaction_count.toLocaleString()} transactions · ${kpis.customer_count.toLocaleString()} customers`,
    },
    {
      label: 'Cash-out at risk',
      value: formatRand(kpis.boundary_cash_out_value),
      hint: `Detected within 30 minutes of inflow · total cash-out ${formatRand(kpis.cash_out_value)}`,
    },
    {
      label: 'Estimated leakage rate',
      value: formatPct(kpis.estimated_leakage_rate),
      hint: `Share of inflows followed by rapid cash-out: ${formatPct(kpis.cash_out_after_inflow_rate)}`,
    },
    {
      label: 'Digital merchant payments',
      value: formatRand(kpis.digital_merchant_payments),
      hint: `${kpis.accepting_merchants} accepting merchants of ${kpis.merchant_count}`,
    },
    {
      label: 'Acceptance opportunities',
      value: kpis.potential_opportunities,
      hint: `Across ${kpis.location_count} locations in scope`,
    },
    {
      label: 'Estimated recoverable value',
      value: formatRand(kpis.estimated_recoverable_value),
      hint: 'Based on a 35% recovery assumption for boundary cash-outs',
    },
  ]

  return (
    <div className="panel">
      {scope && (
        <div className="disclaimer" style={{ marginBottom: 14 }}>
          Territory: <strong>{scope.region}</strong>
          {scope.national ? ' · National view' : ' · Regional view'}
          {scope.last_refreshed
            ? ` · Dataset updated ${new Date(scope.last_refreshed).toLocaleString()}`
            : ''}
        </div>
      )}
      <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(3, minmax(0, 1fr))' }}>
        {cards.map((c) => (
          <div className="kpi" key={c.label}>
            <div className="label">{c.label}</div>
            <div className="value">{c.value}</div>
            <div className="hint">{c.hint}</div>
          </div>
        ))}
      </div>

      <div className="grid-2">
        <div className="card">
          <h2>Transaction value trend</h2>
          <p className="sub">
            Daily value by transaction type
            {scope?.region ? ` for ${scope.region}` : ''}
          </p>
          <div style={{ width: '100%', height: 280 }}>
            <ResponsiveContainer>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="gCash" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#e85d04" stopOpacity={0.45} />
                    <stop offset="100%" stopColor="#e85d04" stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="gMerch" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#0d7377" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="#0d7377" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
                <Tooltip formatter={(v) => formatRand(v)} />
                <Legend />
                <Area type="monotone" dataKey="Cash-out" stroke="#e85d04" fill="url(#gCash)" strokeWidth={2} />
                <Area
                  type="monotone"
                  dataKey="Merchant payment"
                  stroke="#0d7377"
                  fill="url(#gMerch)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <h2>How MoMo Loop helps</h2>
          <p className="sub">
            When customers receive money but cannot pay the next merchant digitally, value exits the
            MoMo ecosystem as cash.
          </p>
          <ol className="reason-list" style={{ paddingLeft: 18, fontSize: '0.9rem' }}>
            <li>Detect probable cash-out boundaries from inflow and withdrawal patterns.</li>
            <li>Identify locations and merchant categories with weak acceptance coverage.</li>
            <li>Prioritise onboarding where expanding acceptance retains the most digital value.</li>
          </ol>
          <div className="disclaimer">{disclaimer}</div>
        </div>
      </div>
    </div>
  )
}
