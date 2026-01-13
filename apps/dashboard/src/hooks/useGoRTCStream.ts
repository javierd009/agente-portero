'use client'

import { useEffect, useRef, useState, useCallback } from 'react'

interface UseGoRTCStreamOptions {
  streamName: string
  go2rtcUrl?: string
  autoConnect?: boolean
  onError?: (error: Error) => void
  onConnected?: () => void
  onDisconnected?: () => void
}

interface UseGoRTCStreamReturn {
  videoRef: React.RefObject<HTMLVideoElement | null>
  isConnecting: boolean
  isConnected: boolean
  error: Error | null
  connect: () => Promise<void>
  disconnect: () => void
  takeSnapshot: () => string | null
}

/**
 * Hook para conectar a streams de go2rtc via WebRTC
 *
 * @example
 * ```tsx
 * const { videoRef, isConnected, error } = useGoRTCStream({
 *   streamName: 'entrada_main',
 *   go2rtcUrl: 'http://172.20.20.1:1984'
 * })
 *
 * return <video ref={videoRef} autoPlay muted />
 * ```
 */
export function useGoRTCStream({
  streamName,
  go2rtcUrl = process.env.NEXT_PUBLIC_GO2RTC_URL || 'http://localhost:1984',
  autoConnect = true,
  onError,
  onConnected,
  onDisconnected,
}: UseGoRTCStreamOptions): UseGoRTCStreamReturn {
  const videoRef = useRef<HTMLVideoElement>(null)
  const pcRef = useRef<RTCPeerConnection | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  const [isConnecting, setIsConnecting] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    if (pcRef.current) {
      pcRef.current.close()
      pcRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setIsConnected(false)
    onDisconnected?.()
  }, [onDisconnected])

  const connect = useCallback(async () => {
    if (isConnecting || isConnected) return

    setIsConnecting(true)
    setError(null)

    try {
      // Crear RTCPeerConnection
      const pc = new RTCPeerConnection({
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' },
        ],
      })
      pcRef.current = pc

      // Configurar recepción de tracks
      pc.ontrack = (event) => {
        if (videoRef.current && event.streams[0]) {
          videoRef.current.srcObject = event.streams[0]
        }
      }

      // Monitorear estado de conexión
      pc.onconnectionstatechange = () => {
        if (pc.connectionState === 'connected') {
          setIsConnected(true)
          setIsConnecting(false)
          onConnected?.()
        } else if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
          const err = new Error(`Connection ${pc.connectionState}`)
          setError(err)
          setIsConnected(false)
          onError?.(err)
        }
      }

      // Agregar transceivers para recibir audio y video
      pc.addTransceiver('video', { direction: 'recvonly' })
      pc.addTransceiver('audio', { direction: 'recvonly' })

      // Crear oferta SDP
      const offer = await pc.createOffer()
      await pc.setLocalDescription(offer)

      // Conectar via WebSocket a go2rtc
      const wsProtocol = go2rtcUrl.startsWith('https') ? 'wss' : 'ws'
      const wsHost = go2rtcUrl.replace(/^https?:\/\//, '')
      const wsUrl = `${wsProtocol}://${wsHost}/api/ws?src=${encodeURIComponent(streamName)}`

      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        // Enviar oferta SDP
        ws.send(JSON.stringify({
          type: 'offer',
          sdp: offer.sdp,
        }))
      }

      ws.onmessage = async (event) => {
        const msg = JSON.parse(event.data)

        if (msg.type === 'answer') {
          await pc.setRemoteDescription(new RTCSessionDescription({
            type: 'answer',
            sdp: msg.sdp,
          }))
        } else if (msg.type === 'candidate' && msg.candidate) {
          await pc.addIceCandidate(new RTCIceCandidate(msg.candidate))
        }
      }

      ws.onerror = (event) => {
        const err = new Error('WebSocket error')
        setError(err)
        setIsConnecting(false)
        onError?.(err)
      }

      ws.onclose = () => {
        if (isConnected) {
          disconnect()
        }
      }

      // Enviar ICE candidates
      pc.onicecandidate = (event) => {
        if (event.candidate && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            type: 'candidate',
            candidate: event.candidate,
          }))
        }
      }

    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err))
      setError(error)
      setIsConnecting(false)
      onError?.(error)
    }
  }, [streamName, go2rtcUrl, isConnecting, isConnected, onConnected, onError, disconnect])

  // Tomar snapshot del video actual
  const takeSnapshot = useCallback((): string | null => {
    if (!videoRef.current) return null

    const video = videoRef.current
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight

    const ctx = canvas.getContext('2d')
    if (!ctx) return null

    ctx.drawImage(video, 0, 0)
    return canvas.toDataURL('image/jpeg', 0.9)
  }, [])

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [autoConnect, connect, disconnect])

  return {
    videoRef,
    isConnecting,
    isConnected,
    error,
    connect,
    disconnect,
    takeSnapshot,
  }
}
