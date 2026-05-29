const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

async function request(path, options) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  })
  if (!response.ok) {
    const error = new Error(`Error API ${response.status}`)
    try {
      const payload = await response.json()
      error.detail = payload.detail
    } catch {
      error.detail = null
    }
    throw error
  }
  return response.json()
}

export const claimsApi = {
  health: () => request('/api/health'),
  systemStatus: () => request('/api/system/status'),
  claims: () => request('/api/claims'),
  claim: (id) => request(`/api/claims/${id}`),
  summary: () => request('/api/dashboard/summary'),
  topRisk: () => request('/api/risk/top'),
  providers: () => request('/api/providers/ranking'),
  cities: () => request('/api/cities/ranking'),
  report: () => request('/api/reports/executive-summary'),
  agentStatus: () => request('/api/agent/status'),
  databaseStatus: () => request('/api/database/status'),
  syncDatabase: () => request('/api/database/sync', { method: 'POST' }),
  generateDataset: (count, riskMix) => request('/api/dataset/generate', { method: 'POST', body: JSON.stringify({ count, risk_mix: riskMix }) }),
  hackiaSummary: () => request('/api/hackia/summary'),
  hackiaClaims: () => request('/api/hackia/claims'),
  hackiaTables: () => request('/api/hackia/tables'),
  hackiaPdfs: () => request('/api/hackia/pdfs'),
  hackiaPdfDownloadUrl: (id) => `${API_BASE}/api/hackia/pdfs/${encodeURIComponent(id)}/download`,
  hackiaClaim: (id) => request(`/api/hackia/claims/${id}`),
  hackiaRecalculate: () => request('/api/hackia/recalculate', { method: 'POST' }),
  hackiaClearLegacy: () => request('/api/hackia/clear-legacy', { method: 'POST' }),
  hackiaClear: () => request('/api/hackia/clear', { method: 'POST' }),
  agentConversations: () => request('/api/agent/conversations'),
  createConversation: () => request('/api/agent/conversations', { method: 'POST' }),
  deleteConversation: (id) => request(`/api/agent/conversations/${id}`, { method: 'DELETE' }),
  renameConversation: (id, title) => request(`/api/agent/conversations/${id}`, { method: 'PATCH', body: JSON.stringify({ title }) }),
  agentHistory: (conversationId) => request(`/api/agent/conversations/${conversationId}/messages`),
  deleteHistoryMessage: (id) => request(`/api/agent/history/${id}`, { method: 'DELETE' }),
  moveHistoryMessage: (id, direction) => request(`/api/agent/history/${id}/move`, { method: 'POST', body: JSON.stringify({ direction }) }),
  chat: (message, conversationId) => request('/api/agent/chat', { method: 'POST', body: JSON.stringify({ message, conversation_id: conversationId }) }),
  reviewActions: (claimId) => request(`/api/claims/${claimId}/review-actions`),
  createReviewAction: (claimId, status, note) => request(`/api/claims/${claimId}/review-action`, { method: 'POST', body: JSON.stringify({ status, note }) }),
  upload: async (file) => {
    const form = new FormData()
    form.append('file', file)
    const response = await fetch(`${API_BASE}/api/upload`, { method: 'POST', body: form })
    if (!response.ok) {
      const error = new Error(`Error API ${response.status}`)
      try {
        const payload = await response.json()
        error.detail = payload.detail
      } catch {
        error.detail = null
      }
      throw error
    }
    return response.json()
  },
  uploadHackiaExcel: async (file) => {
    const form = new FormData()
    form.append('file', file)
    const response = await fetch(`${API_BASE}/api/hackia/import-excel`, { method: 'POST', body: form })
    if (!response.ok) {
      const error = new Error(`Error API ${response.status}`)
      try {
        const payload = await response.json()
        error.detail = payload.detail
      } catch {
        error.detail = null
      }
      throw error
    }
    return response.json()
  },
  uploadHackiaPdfs: async (files) => {
    const form = new FormData()
    Array.from(files).forEach((file) => form.append('files', file))
    const response = await fetch(`${API_BASE}/api/hackia/import-pdfs`, { method: 'POST', body: form })
    if (!response.ok) {
      const error = new Error(`Error API ${response.status}`)
      try {
        const payload = await response.json()
        error.detail = payload.detail
      } catch {
        error.detail = null
      }
      throw error
    }
    return response.json()
  }
}
