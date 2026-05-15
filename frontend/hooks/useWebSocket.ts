import { useEffect, useRef, useCallback } from 'react'

const WS_BASE = import.meta.env.VITE_API_URL?.replace('http', 'ws') || 'ws://localhost:8000'

interface OrderEvent {
  event: string
  order_id?: number
  status?: string
  eta?: string
  rider_lat?: number
  rider_lng?: number
  message?: string
}

interface UseWebSocketOptions {
  orderId: number | null
  onMessage: (event: OrderEvent) => void
  onConnect?: () => void
  onDisconnect?: () => void
}

export function useWebSocket({ orderId, onMessage, onConnect, onDisconnect }: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null)
  const pingInterval = useRef<ReturnType<typeof setInterval> | null>(null)
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)
  const shouldReconnect = useRef(true)

  const connect = useCallback(() => {
    if (!orderId) return
    const url = `${WS_BASE}/ws/orders/${orderId}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      onConnect?.()
      pingInterval.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping')
      }, 30000)
    }

    ws.onmessage = (e) => {
      try {
        const data: OrderEvent = JSON.parse(e.data)
        if (data.event !== 'pong') onMessage(data)
      } catch {}
    }

    ws.onclose = () => {
      onDisconnect?.()
      if (pingInterval.current) clearInterval(pingInterval.current)
      if (shouldReconnect.current) {
        reconnectTimeout.current = setTimeout(connect, 3000)
      }
    }

    ws.onerror = () => ws.close()
  }, [orderId, onMessage, onConnect, onDisconnect])

  useEffect(() => {
    shouldReconnect.current = true
    connect()
    return () => {
      shouldReconnect.current = false
      if (pingInterval.current) clearInterval(pingInterval.current)
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current)
      wsRef.current?.close()
    }
  }, [connect])

  const send = useCallback((data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  return { send }
}