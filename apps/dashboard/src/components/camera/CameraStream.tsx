'use client'

import { useState } from 'react'
import { useGoRTCStream } from '@/hooks/useGoRTCStream'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Loader2,
  AlertTriangle,
  Video,
  VideoOff,
  Camera,
  Maximize2,
  Volume2,
  VolumeX,
} from 'lucide-react'

interface CameraStreamProps {
  streamName: string
  title?: string
  go2rtcUrl?: string
  showControls?: boolean
  aspectRatio?: '16/9' | '4/3' | '1/1'
  className?: string
  onSnapshot?: (imageData: string) => void
}

/**
 * Componente de video en vivo para cámaras via go2rtc/WebRTC
 *
 * @example
 * ```tsx
 * <CameraStream
 *   streamName="entrada_main"
 *   title="Puerta Principal"
 *   go2rtcUrl="http://172.20.20.1:1984"
 * />
 * ```
 */
export function CameraStream({
  streamName,
  title,
  go2rtcUrl,
  showControls = true,
  aspectRatio = '16/9',
  className = '',
  onSnapshot,
}: CameraStreamProps) {
  const [isMuted, setIsMuted] = useState(true)
  const [isFullscreen, setIsFullscreen] = useState(false)

  const {
    videoRef,
    isConnecting,
    isConnected,
    error,
    connect,
    disconnect,
    takeSnapshot,
  } = useGoRTCStream({
    streamName,
    go2rtcUrl,
    autoConnect: true,
  })

  const handleSnapshot = () => {
    const imageData = takeSnapshot()
    if (imageData && onSnapshot) {
      onSnapshot(imageData)
    } else if (imageData) {
      // Download snapshot
      const link = document.createElement('a')
      link.href = imageData
      link.download = `snapshot-${streamName}-${Date.now()}.jpg`
      link.click()
    }
  }

  const handleFullscreen = () => {
    const video = videoRef.current
    if (!video) return

    if (!document.fullscreenElement) {
      video.requestFullscreen()
      setIsFullscreen(true)
    } else {
      document.exitFullscreen()
      setIsFullscreen(false)
    }
  }

  const handleMuteToggle = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted
      setIsMuted(!isMuted)
    }
  }

  const aspectRatioClass = {
    '16/9': 'aspect-video',
    '4/3': 'aspect-[4/3]',
    '1/1': 'aspect-square',
  }[aspectRatio]

  return (
    <Card className={className}>
      {title && (
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center justify-between text-base">
            <span className="flex items-center gap-2">
              <Video className="h-4 w-4" />
              {title}
            </span>
            {isConnected && (
              <span className="flex items-center gap-1.5 text-xs font-normal text-green-600">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
                </span>
                En vivo
              </span>
            )}
          </CardTitle>
        </CardHeader>
      )}

      <CardContent className="p-2">
        {/* Video Container */}
        <div className={`relative w-full ${aspectRatioClass} bg-black rounded-lg overflow-hidden`}>
          <video
            ref={videoRef}
            autoPlay
            muted={isMuted}
            playsInline
            className="absolute inset-0 h-full w-full object-contain"
          />

          {/* Loading Overlay */}
          {isConnecting && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/60">
              <div className="flex flex-col items-center gap-2 text-white">
                <Loader2 className="h-8 w-8 animate-spin" />
                <span className="text-sm">Conectando...</span>
              </div>
            </div>
          )}

          {/* Error Overlay */}
          {error && !isConnecting && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/80">
              <div className="flex flex-col items-center gap-2 text-center p-4">
                <AlertTriangle className="h-8 w-8 text-red-500" />
                <span className="text-sm text-white font-medium">Error de conexión</span>
                <span className="text-xs text-gray-300">{error.message}</span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => connect()}
                  className="mt-2"
                >
                  Reintentar
                </Button>
              </div>
            </div>
          )}

          {/* Offline Overlay */}
          {!isConnecting && !isConnected && !error && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/60">
              <div className="flex flex-col items-center gap-2 text-white">
                <VideoOff className="h-8 w-8" />
                <span className="text-sm">Stream desconectado</span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => connect()}
                  className="mt-2"
                >
                  Conectar
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Controls */}
        {showControls && (
          <div className="mt-2 flex items-center justify-between">
            <div className="flex gap-1">
              <Button
                size="sm"
                variant="ghost"
                onClick={handleMuteToggle}
                title={isMuted ? 'Activar sonido' : 'Silenciar'}
              >
                {isMuted ? (
                  <VolumeX className="h-4 w-4" />
                ) : (
                  <Volume2 className="h-4 w-4" />
                )}
              </Button>

              <Button
                size="sm"
                variant="ghost"
                onClick={handleSnapshot}
                title="Tomar captura"
                disabled={!isConnected}
              >
                <Camera className="h-4 w-4" />
              </Button>

              <Button
                size="sm"
                variant="ghost"
                onClick={handleFullscreen}
                title="Pantalla completa"
                disabled={!isConnected}
              >
                <Maximize2 className="h-4 w-4" />
              </Button>
            </div>

            <div className="text-xs text-muted-foreground">
              {streamName}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
