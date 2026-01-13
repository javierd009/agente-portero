'use client'

import { useState } from 'react'
import { CameraStream } from './CameraStream'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Grid2X2, Grid3X3, LayoutGrid, Maximize2 } from 'lucide-react'

interface CameraConfig {
  id: string
  streamName: string
  title: string
}

interface CameraGridProps {
  cameras: CameraConfig[]
  go2rtcUrl?: string
  defaultLayout?: '2x2' | '3x3' | '4x4' | '1x1'
}

/**
 * Grid de múltiples cámaras con layouts configurables
 *
 * @example
 * ```tsx
 * <CameraGrid
 *   cameras={[
 *     { id: '1', streamName: 'entrada_main', title: 'Entrada' },
 *     { id: '2', streamName: 'estacionamiento', title: 'Estacionamiento' },
 *   ]}
 *   go2rtcUrl="http://172.20.20.1:1984"
 *   defaultLayout="2x2"
 * />
 * ```
 */
export function CameraGrid({
  cameras,
  go2rtcUrl,
  defaultLayout = '2x2',
}: CameraGridProps) {
  const [layout, setLayout] = useState(defaultLayout)
  const [selectedCamera, setSelectedCamera] = useState<string | null>(null)

  const gridClasses = {
    '1x1': 'grid-cols-1',
    '2x2': 'grid-cols-1 md:grid-cols-2',
    '3x3': 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
    '4x4': 'grid-cols-2 md:grid-cols-3 lg:grid-cols-4',
  }

  const layoutIcons = {
    '1x1': <Maximize2 className="h-4 w-4" />,
    '2x2': <Grid2X2 className="h-4 w-4" />,
    '3x3': <Grid3X3 className="h-4 w-4" />,
    '4x4': <LayoutGrid className="h-4 w-4" />,
  }

  // Si hay una cámara seleccionada, mostrar solo esa en grande
  if (selectedCamera) {
    const camera = cameras.find((c) => c.id === selectedCamera)
    if (camera) {
      return (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">{camera.title}</h3>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSelectedCamera(null)}
            >
              Volver a grid
            </Button>
          </div>
          <CameraStream
            streamName={camera.streamName}
            title={camera.title}
            go2rtcUrl={go2rtcUrl}
            showControls={true}
            aspectRatio="16/9"
            className="max-w-4xl mx-auto"
          />
        </div>
      )
    }
  }

  return (
    <div className="space-y-4">
      {/* Layout Controls */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          {cameras.length} cámara{cameras.length !== 1 ? 's' : ''}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Layout:</span>
          <Select value={layout} onValueChange={(v) => setLayout(v as typeof layout)}>
            <SelectTrigger className="w-24">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1x1">
                <span className="flex items-center gap-2">
                  {layoutIcons['1x1']} 1x1
                </span>
              </SelectItem>
              <SelectItem value="2x2">
                <span className="flex items-center gap-2">
                  {layoutIcons['2x2']} 2x2
                </span>
              </SelectItem>
              <SelectItem value="3x3">
                <span className="flex items-center gap-2">
                  {layoutIcons['3x3']} 3x3
                </span>
              </SelectItem>
              <SelectItem value="4x4">
                <span className="flex items-center gap-2">
                  {layoutIcons['4x4']} 4x4
                </span>
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Camera Grid */}
      <div className={`grid gap-4 ${gridClasses[layout]}`}>
        {cameras.map((camera) => (
          <div
            key={camera.id}
            className="cursor-pointer transition-transform hover:scale-[1.02]"
            onDoubleClick={() => setSelectedCamera(camera.id)}
          >
            <CameraStream
              streamName={camera.streamName}
              title={camera.title}
              go2rtcUrl={go2rtcUrl}
              showControls={layout === '1x1' || layout === '2x2'}
              aspectRatio="16/9"
            />
          </div>
        ))}
      </div>

      {cameras.length > 1 && (
        <p className="text-xs text-center text-muted-foreground">
          Doble clic en una cámara para verla en pantalla completa
        </p>
      )}
    </div>
  )
}
