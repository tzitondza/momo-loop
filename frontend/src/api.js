const TOKEN_KEY = 'momo_loop_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

async function request(path, { method = 'GET', params, body, form, auth = true } = {}) {
  const qs = new URLSearchParams(
    Object.entries(params || {}).filter(([, v]) => v !== null && v !== undefined && v !== '')
  )
  const url = qs.toString() ? `${path}?${qs}` : path
  const headers = {}
  if (auth) {
    const token = getToken()
    if (token) headers.Authorization = `Bearer ${token}`
  }

  let payload
  if (form) {
    payload = form
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }

  const res = await fetch(url, { method, headers, body: payload })
  if (res.status === 204) return null

  let data = null
  const text = await res.text()
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = { detail: text }
    }
  }

  if (!res.ok) {
    if (res.status === 401 && auth) {
      clearToken()
    }
    const detail = data?.detail
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg || JSON.stringify(d)).join(', ')
          : `API ${res.status}: ${path}`
    const err = new Error(message)
    err.status = res.status
    throw err
  }
  return data
}

async function downloadExport(path, fallbackName) {
  const token = getToken()
  const res = await fetch(path, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) {
    let message = `Export failed (${res.status})`
    try {
      const data = await res.json()
      if (typeof data?.detail === 'string') message = data.detail
    } catch {
      /* ignore */
    }
    throw new Error(message)
  }
  const blob = await res.blob()
  const disposition = res.headers.get('Content-Disposition') || ''
  const match = disposition.match(/filename="?([^"]+)"?/)
  const filename = match?.[1] || fallbackName
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export const api = {
  login(email, password) {
    const form = new URLSearchParams()
    form.set('username', email)
    form.set('password', password)
    return request('/api/auth/login', { method: 'POST', form, auth: false })
  },
  me: () => request('/api/auth/me'),
  overview: () => request('/api/overview'),
  boundaries: (params) => request('/api/boundaries', { params }),
  opportunities: (limit = 25) => request('/api/opportunities', { params: { limit } }),
  meta: () => request('/api/meta'),
  exportOpportunities(limit = 100, format = 'csv') {
    return downloadExport(
      `/api/opportunities/export?limit=${limit}&format=${format}`,
      `momo-loop-opportunities.${format === 'pdf' ? 'pdf' : 'csv'}`
    )
  },
  map: () => request('/api/map'),
  simulate: (params) => request('/api/simulate', { params }),
  filters: () => request('/api/filters'),
  listScenarios: () => request('/api/scenarios'),
  createScenario: (body) => request('/api/scenarios', { method: 'POST', body }),
  deleteScenario: (id) => request(`/api/scenarios/${id}`, { method: 'DELETE' }),
  listPipeline: (params) => request('/api/pipeline', { params }),
  createPipeline: (body) => request('/api/pipeline', { method: 'POST', body }),
  updatePipeline: (id, body) => request(`/api/pipeline/${id}`, { method: 'PATCH', body }),
  deletePipeline: (id) => request(`/api/pipeline/${id}`, { method: 'DELETE' }),
  listAudit: (limit = 30) => request('/api/audit', { params: { limit } }),
  listUsers: () => request('/api/users'),
  listAssignees: () => request('/api/assignees'),
  getConfig: () => request('/api/admin/config'),
  refreshData: () => request('/api/admin/refresh-data', { method: 'POST' }),
  async uploadDataset(dataset, file) {
    const token = getToken()
    const form = new FormData()
    form.set('dataset', dataset)
    form.set('file', file)
    const res = await fetch('/api/admin/upload', {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    })
    const text = await res.text()
    let data = null
    try {
      data = text ? JSON.parse(text) : null
    } catch {
      data = { detail: text }
    }
    if (!res.ok) {
      const detail = data?.detail
      throw new Error(typeof detail === 'string' ? detail : `Upload failed (${res.status})`)
    }
    return data
  },
}

export function formatRand(value) {
  if (value == null || Number.isNaN(Number(value))) return 'R—'
  return `R${Number(value).toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`
}

export function formatPct(value, digits = 1) {
  if (value == null) return '—'
  return `${(Number(value) * 100).toFixed(digits)}%`
}
