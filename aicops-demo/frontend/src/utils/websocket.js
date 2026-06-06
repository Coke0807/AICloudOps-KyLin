/**
 * WebSocket 实时监控客户端
 * 自动重连 + 心跳保活 + 指数退避
 */
import { ref, onUnmounted } from 'vue'

export function useWebSocket(path = '/api/v1/ws/monitor') {
  const data = ref(null)
  const connected = ref(false)
  let ws = null
  let reconnectTimer = null
  let heartbeatTimer = null
  let reconnectAttempts = 0
  const MAX_RECONNECT_ATTEMPTS = 10

  function connect() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${location.host}${path}`

    ws = new WebSocket(url)

    ws.onopen = () => {
      connected.value = true
      reconnectAttempts = 0
      heartbeatTimer = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping')
      }, 25000)
    }

    ws.onmessage = (event) => {
      try {
        data.value = JSON.parse(event.data)
      } catch {
        data.value = event.data
      }
    }

    ws.onclose = () => {
      connected.value = false
      clearInterval(heartbeatTimer)
      // 指数退避重连，最多 10 次
      if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        const delay = Math.min(3000 * Math.pow(1.5, reconnectAttempts), 30000)
        reconnectTimer = setTimeout(() => {
          reconnectAttempts++
          connect()
        }, delay)
      }
    }

    ws.onerror = () => ws.close()
  }

  function disconnect() {
    clearTimeout(reconnectTimer)
    clearInterval(heartbeatTimer)
    ws?.close()
  }

  function requestStatus() {
    if (ws?.readyState === WebSocket.OPEN) ws.send('status')
  }

  connect()

  return { data, connected, disconnect, requestStatus }
}
