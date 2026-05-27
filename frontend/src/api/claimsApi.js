const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

async function request(path, options) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  })
  if (!response.ok) {
    throw new Error(`Error API ${response.status}`)
  }
  return response.json()
}

export const claimsApi = {
  health: () => request('/api/health'),
  claims: () => request('/api/claims'),
  claim: (id) => request(`/api/claims/${id}`),
  summary: () => request('/api/dashboard/summary'),
  topRisk: () => request('/api/risk/top'),
  providers: () => request('/api/providers/ranking'),
  cities: () => request('/api/cities/ranking'),
  report: () => request('/api/reports/executive-summary'),
  chat: (message) => request('/api/agent/chat', { method: 'POST', body: JSON.stringify({ message }) }),
  upload: async (file) => {
    const form = new FormData()
    form.append('file', file)
    const response = await fetch(`${API_BASE}/api/upload`, { method: 'POST', body: form })
    if (!response.ok) throw new Error(`Error API ${response.status}`)
    return response.json()
  }
}
