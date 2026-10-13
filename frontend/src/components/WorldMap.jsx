import React, { useState, useCallback, useEffect } from 'react'
import { ComposableMap, Geographies, Geography, ZoomableGroup } from 'react-simple-maps'
import { 
  Globe, Layers, MapPin, Clock, Satellite, 
  ChevronDown, ChevronUp, Pin, Eye, EyeOff,
  Navigation, RotateCw, ZoomIn, ZoomOut, Maximize2
} from 'lucide-react'
import { T as C } from '../theme'

// World Monitor style map regions
const REGIONS = [
  { id: 'global', label: 'Global', center: [0, 20], zoom: 1 },
  { id: 'americas', label: 'Americas', center: [-100, 35], zoom: 2 },
  { id: 'europe', label: 'Europe', center: [15, 50], zoom: 3 },
  { id: 'mena', label: 'MENA', center: [25, 25], zoom: 3 },
  { id: 'asia', label: 'Asia', center: [100, 35], zoom: 2.5 },
  { id: 'latam', label: 'Latin America', center: [-60, -15], zoom: 2.5 },
  { id: 'africa', label: 'Africa', center: [20, 0], zoom: 2.5 },
  { id: 'oceania', label: 'Oceania', center: [135, -25], zoom: 3 },
]

// Data layers categories
const LAYER_CATEGORIES = {
  markets: { label: 'Markets', color: C.green, layers: ['stocks', 'crypto', 'commodities', 'forex'] },
  companies: { label: 'Companies', color: C.blue, layers: ['headquarters', 'suppliers', 'customers'] },
  risks: { label: 'Risks', color: C.red, layers: ['geopolitical', 'supply_chain', 'regulatory'] },
  events: { label: 'Events', color: C.orange, layers: ['earnings', 'conferences', 'announcements'] },
}

const TIME_RANGES = [
  { id: '1h', label: '1h' },
  { id: '6h', label: '6h' },
  { id: '24h', label: '24h' },
  { id: '48h', label: '48h' },
  { id: '7d', label: '7d' },
  { id: 'all', label: 'All' },
]

export default function WorldMap({ onRegionChange, onLayerToggle, activeLayers, timeRange, onTimeRangeChange, onCountrySelect, selectedCountry }) {
  const [geoUrl, setGeoUrl] = useState(null)
  const [position, setPosition] = useState({ coordinates: [0, 20], zoom: 1 })
  const [activeRegion, setActiveRegion] = useState('global')
  const [showControls, setShowControls] = useState(false)
  const [showLayers, setShowLayers] = useState(false)
  const [isPinned, setIsPinned] = useState(false)
  const [is3D, setIs3D] = useState(false)

  useEffect(() => {
    // Served from public/ rather than raw.githubusercontent.com: a third-party
    // CDN has no business in the data path, and this copy carries iso2/iso3,
    // which the upstream file does not.
    setGeoUrl('/world-countries.geojson')
  }, [])

  const handleRegionClick = useCallback((region) => {
    setActiveRegion(region.id)
    setPosition({ coordinates: region.center, zoom: region.zoom })
    onRegionChange?.(region.id)
  }, [onRegionChange])

  const handleZoomIn = useCallback(() => {
    setPosition(prev => ({ ...prev, zoom: Math.min(prev.zoom + 0.5, 8) }))
  }, [])

  const handleZoomOut = useCallback(() => {
    setPosition(prev => ({ ...prev, zoom: Math.max(prev.zoom - 0.5, 1) }))
  }, [])

  const handleReset = useCallback(() => {
    setPosition({ coordinates: [0, 20], zoom: 1 })
    setActiveRegion('global')
  }, [])

  const toggleLayer = useCallback((layerId) => {
    onLayerToggle?.(layerId)
  }, [onLayerToggle])

  const togglePin = useCallback(() => {
    setIsPinned(prev => !prev)
  }, [])

  if (!geoUrl) {
    return (
      <div className="flex items-center justify-center h-full" style={{ background: C.bgDeep }}>
        <div className="text-center space-y-3">
          <Globe size={24} className="mx-auto animate-pulse" style={{ color: C.dim }} />
          <p className="text-[10px] font-mono" style={{ color: C.muted }}>Loading map data...</p>
        </div>
      </div>
    )
  }

  return (
    <div 
      className={`relative ${isPinned ? 'sticky top-0 z-50' : ''}`}
      style={{ 
        background: C.bgDeep,
        borderBottom: `1px solid ${C.border}`,
        transition: 'all 0.2s ease'
      }}
    >
      {/* Map container - mobile responsive height */}
      <div className="relative" style={{ height: isPinned ? '45vh' : '40vh' }}>
        <ComposableMap
          projection={is3D ? "geoOrthographic" : "geoMercator"}
          projectionConfig={{ scale: is3D ? 220 : 150 }}
          style={{ width: '100%', height: '100%', background: C.bgDeep }}
        >
          <ZoomableGroup
            zoom={position.zoom}
            center={position.coordinates}
            onMoveEnd={setPosition}
          >
            <Geographies geography={geoUrl}>
              {({ geographies }) =>
                geographies.map((geo) => {
                  const iso2 = geo.properties?.iso2
                  const isSelected = iso2 && iso2 === selectedCountry
                  // The three disputed territories carry no ISO code and so
                  // have nothing to look up; they stay visible but inert.
                  const clickable = Boolean(iso2 && onCountrySelect)
                  return (
                    <Geography
                      key={geo.rsmKey}
                      geography={geo}
                      onClick={clickable ? () => onCountrySelect(iso2, geo.properties.name) : undefined}
                      style={{
                        default: {
                          fill: isSelected ? C.blue : C.panel,
                          stroke: isSelected ? C.blue : C.border,
                          strokeWidth: isSelected ? 1.2 : 0.5,
                          outline: 'none',
                          cursor: clickable ? 'pointer' : 'default',
                        },
                        hover: {
                          fill: clickable ? C.cardHover : C.panel,
                          stroke: clickable ? C.blue : C.border,
                          strokeWidth: 1,
                          outline: 'none',
                          cursor: clickable ? 'pointer' : 'default',
                        },
                        pressed: { fill: C.card, stroke: C.blue, strokeWidth: 1, outline: 'none' },
                      }}
                    />
                  )
                })
              }
            </Geographies>
          </ZoomableGroup>
        </ComposableMap>

        {/* Map overlay controls - mobile responsive */}
        <div className="absolute top-3 right-3 flex flex-col gap-2">
          {/* Mobile: simplified controls */}
          <div className="md:hidden flex flex-col gap-1">
            <button
              onClick={togglePin}
              className="w-8 h-8 flex items-center justify-center"
              style={{ 
                background: C.card, 
                border: `1px solid ${isPinned ? C.blue : C.border}`,
                borderRadius: '2px'
              }}
              title={isPinned ? "Unpin map" : "Pin map while scrolling"}
            >
              <Pin size={14} style={{ color: isPinned ? C.blue : C.muted }} />
            </button>
          </div>

          {/* Desktop: full controls */}
          <div className="hidden md:flex flex-col gap-2">
            {/* Pin button */}
            <button
              onClick={togglePin}
              className="w-8 h-8 flex items-center justify-center"
              style={{ 
                background: C.card, 
                border: `1px solid ${isPinned ? C.blue : C.border}`,
                borderRadius: '2px'
              }}
              title={isPinned ? "Unpin map" : "Pin map while scrolling"}
            >
              <Pin size={14} style={{ color: isPinned ? C.blue : C.muted }} />
            </button>

            {/* 3D/2D toggle */}
            <button
              onClick={() => setIs3D(!is3D)}
              className="w-8 h-8 flex items-center justify-center"
              style={{ 
                background: C.card, 
                border: `1px solid ${is3D ? C.blue : C.border}`,
                borderRadius: '2px'
              }}
              title={is3D ? "Switch to 2D flat map" : "Switch to 3D globe"}
            >
              <Globe size={14} style={{ color: is3D ? C.blue : C.muted }} />
            </button>

            {/* Zoom controls */}
            <div className="flex flex-col gap-1">
              <button
                onClick={handleZoomIn}
                className="w-8 h-8 flex items-center justify-center"
                style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: '2px' }}
                title="Zoom in"
              >
                <ZoomIn size={14} style={{ color: C.muted }} />
              </button>
              <button
                onClick={handleZoomOut}
                className="w-8 h-8 flex items-center justify-center"
                style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: '2px' }}
                title="Zoom out"
              >
                <ZoomOut size={14} style={{ color: C.muted }} />
              </button>
            </div>

            {/* Reset view */}
            <button
              onClick={handleReset}
              className="w-8 h-8 flex items-center justify-center"
              style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: '2px' }}
              title="Reset to global view"
            >
              <RotateCw size={14} style={{ color: C.muted }} />
            </button>
          </div>
        </div>

        {/* Region presets - mobile responsive */}
        <div className="absolute top-3 left-3">
          <button
            onClick={() => setShowControls(!showControls)}
            className="flex items-center gap-2 px-3 py-2"
            style={{ 
              background: C.card, 
              border: `1px solid ${C.border}`,
              borderRadius: '2px'
            }}
          >
            <Navigation size={14} style={{ color: C.blue }} />
            <span className="text-[10px] font-semibold hidden sm:block" style={{ color: C.text }}>
              {REGIONS.find(r => r.id === activeRegion)?.label || 'Global'}
            </span>
            {showControls ? <ChevronUp size={12} style={{ color: C.muted }} /> : <ChevronDown size={12} style={{ color: C.muted }} />}
          </button>

          {showControls && (
            <div 
              className="absolute top-full left-0 mt-1 p-2 space-y-1"
              style={{ 
                background: C.panel, 
                border: `1px solid ${C.border}`,
                borderRadius: '2px',
                minWidth: '140px',
                zIndex: 100
              }}
            >
              {REGIONS.map(region => (
                <button
                  key={region.id}
                  onClick={() => handleRegionClick(region)}
                  className="w-full flex items-center gap-2 px-2 py-1.5 text-left"
                  style={{
                    background: activeRegion === region.id ? C.blueSoft : 'transparent',
                    borderRadius: '2px'
                  }}
                >
                  <span className="text-[10px]" style={{ color: activeRegion === region.id ? C.blue : C.muted }}>
                    {region.label}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Layer controls - mobile responsive */}
        <div className="absolute bottom-3 left-3">
          <button
            onClick={() => setShowLayers(!showLayers)}
            className="flex items-center gap-2 px-3 py-2"
            style={{ 
              background: C.card, 
              border: `1px solid ${C.border}`,
              borderRadius: '2px'
            }}
          >
            <Layers size={14} style={{ color: C.purple }} />
            <span className="text-[10px] font-semibold hidden sm:block" style={{ color: C.text }}>
              Layers
            </span>
            {showLayers ? <ChevronUp size={12} style={{ color: C.muted }} /> : <ChevronDown size={12} style={{ color: C.muted }} />}
          </button>

          {showLayers && (
            <div 
              className="absolute bottom-full left-0 mb-1 p-2 space-y-2"
              style={{ 
                background: C.panel, 
                border: `1px solid ${C.border}`,
                borderRadius: '2px',
                minWidth: '200px',
                maxHeight: '300px',
                overflowY: 'auto',
                zIndex: 100
              }}
            >
              {Object.entries(LAYER_CATEGORIES).map(([catId, category]) => (
                <div key={catId}>
                  <div className="flex items-center gap-2 mb-1">
                    <div 
                      className="w-2 h-2 rounded-full"
                      style={{ background: category.color }}
                    />
                    <span className="text-[9px] font-bold uppercase" style={{ color: category.color }}>
                      {category.label}
                    </span>
                  </div>
                  <div className="space-y-0.5 pl-4">
                    {category.layers.map(layer => (
                      <button
                        key={layer}
                        onClick={() => toggleLayer(layer)}
                        className="w-full flex items-center justify-between px-2 py-1 text-left"
                        style={{
                          background: activeLayers?.includes(layer) ? `${category.color}22` : 'transparent',
                          borderRadius: '2px'
                        }}
                      >
                        <span className="text-[9px]" style={{ color: C.muted }}>
                          {layer.replace('_', ' ')}
                        </span>
                        {activeLayers?.includes(layer) ? (
                          <Eye size={10} style={{ color: category.color }} />
                        ) : (
                          <EyeOff size={10} style={{ color: C.dim }} />
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Time range selector - mobile responsive */}
        <div className="absolute bottom-3 right-3">
          <div className="flex items-center gap-1 px-2 py-1.5"
            style={{ 
              background: C.card, 
              border: `1px solid ${C.border}`,
              borderRadius: '2px'
            }}
          >
            <Clock size={12} style={{ color: C.muted }} />
            <div className="hidden sm:flex items-center gap-1">
              {TIME_RANGES.map(range => (
                <button
                  key={range.id}
                  onClick={() => onTimeRangeChange?.(range.id)}
                  className="px-2 py-0.5 text-[9px] font-semibold"
                  style={{
                    background: timeRange === range.id ? C.blueSoft : 'transparent',
                    color: timeRange === range.id ? C.blue : C.muted,
                    borderRadius: '2px'
                  }}
                >
                  {range.label}
                </button>
              ))}
            </div>
            {/* Mobile: show current time range only */}
            <div className="sm:hidden">
              <span className="text-[9px] font-semibold" style={{ color: C.blue }}>
                {TIME_RANGES.find(r => r.id === timeRange)?.label || '24h'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}