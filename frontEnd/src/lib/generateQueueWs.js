/** 生成进度 WebSocket（后端转发 ComfyUI 事件） */

let socket = null
let reconnectTimer = null
const listeners = new Set()

function wsUrl() {
  if (typeof window === 'undefined') return ''
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws/generate-events`
}

function notify(msg) {
  for (const fn of listeners) {
    try {
      fn(msg)
    } catch {
      /* ignore */
    }
  }
}

function scheduleReconnect() {
  if (reconnectTimer) return
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null
    connectGenerateQueueWs()
  }, 2500)
}

export function subscribeGenerateEvents(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

export function connectGenerateQueueWs() {
  if (typeof window === 'undefined') return
  if (socket?.readyState === WebSocket.OPEN) return

  try {
    socket = new WebSocket(wsUrl())
  } catch {
    scheduleReconnect()
    return
  }

  socket.onmessage = (ev) => {
    try {
      notify(JSON.parse(ev.data))
    } catch {
      /* ignore */
    }
  }

  socket.onclose = () => {
    scheduleReconnect()
  }

  socket.onerror = () => {
    try {
      socket?.close()
    } catch {
      /* ignore */
    }
  }
}

export function disconnectGenerateQueueWs() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (socket) {
    socket.onclose = null
    socket.close()
    socket = null
  }
}

export function isGenerateWsConnected() {
  return socket?.readyState === WebSocket.OPEN
}
