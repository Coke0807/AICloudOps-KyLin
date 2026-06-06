import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export const systemApi = {
  getStatus: () => api.get('/system/status'),
  getProcesses: (limit = 20) => api.get('/system/processes', { params: { limit } }),
  getDisks: () => api.get('/system/disks'),
}

export const toolsApi = {
  list: () => api.get('/tools'),
  execute: (toolName, params = {}) =>
    api.post('/tools/execute', { tool_name: toolName, params }),
}

export const agentApi = {
  process: (prompt, sessionId = null) =>
    api.post('/agent/process', { prompt, session_id: sessionId }),
  stream: async function* (prompt, sessionId = null) {
    const response = await fetch('/api/v1/agent/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, session_id: sessionId }),
    })

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    // buffer 用于处理跨 chunk 边界的 SSE 行
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const lines = buffer.split('\n')
      // 最后一个元素可能是不完整的行，保留到下次处理
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed.startsWith('data: ')) continue
        const data = trimmed.slice(6)
        if (data === '[DONE]') return
        try {
          yield JSON.parse(data)
        } catch {
          // 忽略无法解析的行（如空行、注释等）
        }
      }
    }
    // 处理 buffer 中剩余的数据
    if (buffer.trim().startsWith('data: ')) {
      const data = buffer.trim().slice(6)
      if (data !== '[DONE]') {
        try {
          yield JSON.parse(data)
        } catch {
          // ignore
        }
      }
    }
  },
}

export const tracesApi = {
  list: (limit = 50) => api.get('/traces', { params: { limit } }),
  get: (traceId) => api.get(`/traces/${traceId}`),
}

export const safetyApi = {
  getStats: () => api.get('/safety/stats'),
  getEvents: (limit = 100) => api.get('/safety/events', { params: { limit } }),
}

export const historyApi = {
  list: (limit = 50) => api.get('/history', { params: { limit } }),
  get: (sessionId) => api.get(`/history/${sessionId}`),
  delete: (sessionId) => api.delete(`/history/${sessionId}`),
}

export default api
