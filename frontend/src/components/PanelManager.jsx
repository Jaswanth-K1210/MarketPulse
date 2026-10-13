import React, { useState, useCallback } from 'react'
import { 
  LayoutDashboard, Plus, Settings, Grid3X3,
  Activity, Bell, BookOpen, Star, TrendingUp, BarChart2, Brain
} from 'lucide-react'
import { T as C } from '../theme'

// Available panel types
const PANEL_TYPES = [
  { id: 'market_pulse', label: 'Market Pulse', icon: Activity, description: 'Live situation readout' },
  { id: 'alerts', label: 'Active Alerts', icon: Bell, description: 'Current alerts list' },
  { id: 'news', label: 'Recent News', icon: BookOpen, description: 'Latest articles' },
  { id: 'portfolio', label: 'Portfolio', icon: Star, description: 'Holdings overview' },
  { id: 'trends', label: 'Market Trends', icon: TrendingUp, description: 'Trend analysis' },
  { id: 'stocks', label: 'Stock Prices', icon: BarChart2, description: 'Price tickers' },
  { id: 'intelligence', label: 'Intelligence', icon: Brain, description: 'AI analysis' },
]

// Default panel configuration
const DEFAULT_PANELS = [
  { id: 'market_pulse', type: 'market_pulse', span: 2, active: true },
  { id: 'alerts', type: 'alerts', span: 2, active: true },
  { id: 'news', type: 'news', span: 2, active: true },
  { id: 'portfolio', type: 'portfolio', span: 1, active: true },
  { id: 'stocks', type: 'stocks', span: 1, active: true },
  { id: 'intelligence', type: 'intelligence', span: 3, active: true },
]

export default function PanelManager({ 
  panels = DEFAULT_PANELS, 
  onAddPanel,
  onRemovePanel,
  onTogglePanel,
  onSpanChange 
}) {
  const [showPanelLibrary, setShowPanelLibrary] = useState(false)
  const [showLayoutManager, setShowLayoutManager] = useState(false)

  const handleAddPanel = useCallback((panelType) => {
    const newPanel = {
      id: `${panelType}_${Date.now()}`,
      type: panelType,
      span: 1,
      active: true
    }
    onAddPanel?.(newPanel)
    setShowPanelLibrary(false)
  }, [onAddPanel])

  const handleRemovePanel = useCallback((panelId) => {
    onRemovePanel?.(panelId)
  }, [onRemovePanel])

  const handleTogglePanel = useCallback((panelId, isActive) => {
    onTogglePanel?.(panelId, isActive)
  }, [onTogglePanel])

  const handleSpanChange = useCallback((panelId, newSpan) => {
    onSpanChange?.(panelId, newSpan)
  }, [onSpanChange])

  const activePanelCount = panels.filter(p => p.active).length

  return (
    <div className="flex items-center gap-2 px-3 py-2 border-b"
      style={{ 
        background: C.card, 
        borderColor: C.border,
        height: '36px'
      }}
    >
      {/* Panel count indicator */}
      <div className="flex items-center gap-2">
        <Grid3X3 size={12} style={{ color: C.blue }} />
        <span className="text-[10px] font-semibold" style={{ color: C.text }}>
          {activePanelCount} panels
        </span>
      </div>

      <div className="ml-auto flex items-center gap-1">
        {/* Add panel button */}
        <button
          onClick={() => setShowPanelLibrary(!showPanelLibrary)}
          className="flex items-center gap-1.5 px-2 py-1"
          style={{ 
            background: C.blueSoft, 
            border: `1px solid ${C.blueMid}`,
            borderRadius: '2px'
          }}
          title="Add panel"
        >
          <Plus size={11} style={{ color: C.blue }} />
          <span className="text-[10px] font-semibold" style={{ color: C.blue }}>
            Add Panel
          </span>
        </button>

        {/* Layout manager */}
        <button
          onClick={() => setShowLayoutManager(!showLayoutManager)}
          className="flex items-center gap-1.5 px-2 py-1"
          style={{ 
            background: C.card, 
            border: `1px solid ${C.border}`,
            borderRadius: '2px'
          }}
          title="Manage layout"
        >
          <LayoutDashboard size={11} style={{ color: C.muted }} />
          <span className="text-[10px] font-semibold" style={{ color: C.muted }}>
            Layout
          </span>
        </button>
      </div>

      {/* Panel library dropdown */}
      {showPanelLibrary && (
        <div 
          className="absolute top-full right-0 mt-1 p-2 space-y-1"
          style={{ 
            background: C.panel, 
            border: `1px solid ${C.border}`,
            borderRadius: '2px',
            minWidth: '280px',
            maxHeight: '400px',
            overflowY: 'auto',
            zIndex: 100
          }}
        >
          <div className="text-[9px] font-bold mb-2" style={{ color: C.muted }}>
            Available Panels
          </div>
          {PANEL_TYPES.map(panelType => {
            const Icon = panelType.icon
            const isActive = panels.some(p => p.type === panelType.id && p.active)
            return (
              <button
                key={panelType.id}
                onClick={() => !isActive && handleAddPanel(panelType.id)}
                disabled={isActive}
                className="w-full flex items-center gap-2 px-2 py-2 text-left disabled:opacity-50"
                style={{
                  background: 'transparent',
                  borderRadius: '2px'
                }}
              >
                <Icon size={14} style={{ color: isActive ? C.green : C.dim }} />
                <div className="flex-1">
                  <div className="text-[10px] font-semibold" style={{ color: isActive ? C.green : C.text }}>
                    {panelType.label}
                  </div>
                  <div className="text-[8px]" style={{ color: C.dim }}>
                    {panelType.description}
                  </div>
                </div>
                {isActive && (
                  <span className="text-[8px]" style={{ color: C.green }}>✓</span>
                )}
              </button>
            )
          })}
        </div>
      )}

      {/* Layout manager dropdown */}
      {showLayoutManager && (
        <div 
          className="absolute top-full right-0 mt-1 p-2 space-y-1"
          style={{ 
            background: C.panel, 
            border: `1px solid ${C.border}`,
            borderRadius: '2px',
            minWidth: '320px',
            maxHeight: '400px',
            overflowY: 'auto',
            zIndex: 100
          }}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-[9px] font-bold" style={{ color: C.muted }}>
              Panel Layout
            </span>
            <button
              onClick={() => setShowLayoutManager(false)}
              className="text-[9px]" style={{ color: C.dim }}
            >
              ×
            </button>
          </div>
          
          {panels.map(panel => {
            const panelType = PANEL_TYPES.find(pt => pt.id === panel.type)
            const Icon = panelType?.icon || Settings
            return (
              <div 
                key={panel.id}
                className="flex items-center gap-2 px-2 py-2 border"
                style={{ 
                  background: panel.active ? C.card : 'transparent',
                  borderColor: C.borderDim,
                  borderRadius: '2px'
                }}
              >
                <Icon size={12} style={{ color: panel.active ? C.blue : C.dim }} />
                <span className="text-[10px] flex-1" style={{ color: panel.active ? C.text : C.dim }}>
                  {panelType?.label || panel.type}
                </span>
                
                {/* Span controls */}
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4].map(s => (
                    <button
                      key={s}
                      onClick={() => handleSpanChange(panel.id, s)}
                      disabled={!panel.active}
                      className="w-5 h-5 flex items-center justify-center text-[9px] font-mono disabled:opacity-30"
                      style={{
                        background: panel.span === s ? C.blueSoft : 'transparent',
                        border: `1px solid ${panel.span === s ? C.blueMid : C.border}`,
                        borderRadius: '2px',
                        color: panel.span === s ? C.blue : C.muted
                      }}
                    >
                      {s}
                    </button>
                  ))}
                </div>

                {/* Toggle button */}
                <button
                  onClick={() => handleTogglePanel(panel.id, !panel.active)}
                  className="w-5 h-5 flex items-center justify-center"
                  style={{ 
                    background: panel.active ? 'rgba(248,113,113,0.12)' : 'rgba(74,222,128,0.12)',
                    border: `1px solid ${panel.active ? C.redMid : C.greenMid}`,
                    borderRadius: '2px'
                  }}
                  title={panel.active ? 'Hide panel' : 'Show panel'}
                >
                  {panel.active ? (
                    <span style={{ color: C.red, fontSize: '10px' }}>−</span>
                  ) : (
                    <span style={{ color: C.green, fontSize: '10px' }}>+</span>
                  )}
                </button>

                {/* Remove button */}
                <button
                  onClick={() => handleRemovePanel(panel.id)}
                  className="w-5 h-5 flex items-center justify-center"
                  style={{ 
                    background: 'transparent',
                    borderRadius: '2px'
                  }}
                  title="Remove panel"
                >
                  <span style={{ color: C.dim, fontSize: '10px' }}>×</span>
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}