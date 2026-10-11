import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  timeout: 120000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      if (!window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export const authApi = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
}

export const documentsApi = {
  list: () => api.get('/documents'),
  get: (id) => api.get(`/documents/${id}`),
  status: (id) => api.get(`/documents/${id}/status`),
  questions: (id) => api.get(`/documents/${id}/questions`),
  suggested: (id) => api.get(`/documents/${id}/suggested-questions`),
  delete: (id) => api.delete(`/documents/${id}`),
  upload: (file, onProgress) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/documents/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded * 100) / e.total))
      },
    })
  },
}

export const chatApi = {
  chat: (data) => api.post('/chat', data),
  history: () => api.get('/chat/history'),
  detail: (id) => api.get(`/chat/history/${id}`),
  export: (id) => api.get(`/chat/history/${id}/export`, { responseType: 'blob' }),
  feedback: (id, data) => api.patch(`/chat/messages/${id}/feedback`, data),
  dashboard: () => api.get('/dashboard'),
}

export async function streamChat(payload, handlers) {
  const token = localStorage.getItem('token')
  const res = await fetch(`${API_URL}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Stream failed')
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''
    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data:')) continue
      const raw = line.slice(5).trim()
      if (!raw) continue
      try {
        const event = JSON.parse(raw)
        handlers.onEvent?.(event)
      } catch {
        // ignore malformed chunks
      }
    }
  }
  handlers.onDone?.()
}

export default api
