import React, { useState, useRef } from 'react'
import { 
  GripVertical, X, ChevronDown, ChevronUp, 
  Maximize2, Minimize2, Settings
} from 'lucide-react'
import { T as C } from '../theme'

// World Monitor style configurable panel
// Clamp spans to the columns the dashboard grid has at each breakpoint (1 / md:2 / xl:3).
const SPAN_CLASS = { 2: 'md:col-span-2', 3: 'md:col-span-2 xl:col-span-3', 4: 'md:col-span-2 xl:col-span-3' }

export default function ConfigurablePanel({ 
  icon: Icon, 
  title, 
  color, 
  kicker, 
  right, 
  children, 
  className, 
  style,
  defaultSpan = 1,
  onSpanChange,
  onRemove,
  panelId,
  isActive = true,
  onToggle
}) {
  const [isExpanded, setIsExpanded] = useState(true)
  const [isMaximized, setIsMaximized] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [span, setSpan] = useState(defaultSpan)
  const panelRef = useRef(null)

  const handleSpanChange = (newSpan) => {
    setSpan(newSpan)
    onSpanChange?.(panelId, newSpan)
  }

  const handleToggle = () => {
    const newState = !isExpanded
    setIsExpanded(newState)
    onToggle?.(panelId, newState)
  }

  const handleMaximize = () => {
    setIsMaximized(!isMaximized)
  }

  const handleRemove = () => {
    onRemove?.(panelId)
  }

  if (!isActive) return null

  return (
    <section 
      ref={panelRef}
      className={`flex flex-col border overflow-hidden transition-all duration-200 ${isMaximized ? '' : SPAN_CLASS[span] || ''} ${className || ''}`}
      style={{
        background: C.panel,
        borderColor: C.border,
        gridColumn: isMaximized ? '1 / -1' : undefined,
        gridRow: isMaximized ? '1 / -1' : 'auto',
        minHeight: isExpanded ? '168px' : '44px',
        ...style
      }}
    >
      {/* Panel header with World Monitor style */}
      <header 
        className="flex items-center gap-2 px-3 border-b shrink-0 cursor-move"
        style={{ 
          height: 34, 
          background: C.card, 
          borderColor: C.border,
          userSelect: 'none'
        }}
        onMouseDown={() => {
          // Add drag functionality here if needed
        }}
      >
        {/* Drag handle */}
        <div className="cursor-grab active:cursor-grabbing">
          <GripVertical size={12} style={{ color: C.dim }} />
        </div>

        {/* Icon */}
        {Icon && <Icon size={12} strokeWidth={2.2} style={{ color: color || C.blue }} />}

        {/* Title */}
        <h3 className="text-[10px] font-bold uppercase tracking-[0.12em] whitespace-nowrap truncate min-w-0" style={{ color: C.text }}>
          {title}
        </h3>

        {/* Right side controls */}
        <div className="ml-auto flex items-center gap-1">
          {right && <div className="hidden sm:flex items-center gap-2 mr-2">{right}</div>}

          {/* Expand/Collapse */}
          <button
            onClick={handleToggle}
            className="w-6 h-6 flex items-center justify-center"
            style={{ background: 'transparent', border: 'none' }}
            title={isExpanded ? 'Collapse' : 'Expand'}
          >
            {isExpanded ? (
              <ChevronUp size={12} style={{ color: C.dim }} />
            ) : (
              <ChevronDown size={12} style={{ color: C.dim }} />
            )}
          </button>

          {/* Maximize/Restore */}
          <button
            onClick={handleMaximize}
            className="w-6 h-6 flex items-center justify-center"
            style={{ background: 'transparent', border: 'none' }}
            title={isMaximized ? 'Restore' : 'Maximize'}
          >
            {isMaximized ? (
              <Minimize2 size={12} style={{ color: C.dim }} />
            ) : (
              <Maximize2 size={12} style={{ color: C.dim }} />
            )}
          </button>

          {/* Settings */}
          <div className="relative">
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="w-6 h-6 flex items-center justify-center"
              style={{ background: 'transparent', border: 'none' }}
              title="Panel settings"
            >
              <Settings size={12} style={{ color: C.dim }} />
            </button>

            {showSettings && (
              <div 
                className="absolute top-full right-0 mt-1 p-2 space-y-1"
                style={{ 
                  background: C.panel, 
                  border: `1px solid ${C.border}`,
                  borderRadius: '2px',
                  minWidth: '140px',
                  zIndex: 100
                }}
              >
                <div className="text-[9px] font-bold mb-1" style={{ color: C.muted }}>
                  Panel Span
                </div>
                {[1, 2, 3, 4].map(s => (
                  <button
                    key={s}
                    onClick={() => {
                      handleSpanChange(s)
                      setShowSettings(false)
                    }}
                    className="w-full flex items-center justify-between px-2 py-1 text-left"
                    style={{
                      background: span === s ? C.blueSoft : 'transparent',
                      borderRadius: '2px'
                    }}
                  >
                    <span className="text-[9px]" style={{ color: span === s ? C.blue : C.muted }}>
                      {s} column{s > 1 ? 's' : ''}
                    </span>
                    {span === s && (
                      <span className="text-[8px]" style={{ color: C.blue }}>✓</span>
                    )}
                  </button>
                ))}
                
                <div className="border-t pt-1 mt-1" style={{ borderColor: C.borderDim }}>
                  <button
                    onClick={() => {
                      handleRemove()
                      setShowSettings(false)
                    }}
                    className="w-full flex items-center gap-2 px-2 py-1 text-left"
                    style={{ color: C.red }}
                  >
                    <X size={10} />
                    <span className="text-[9px]">Remove Panel</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Panel content */}
      {isExpanded && (
        <>
          {kicker && (
            <p className="text-[10px] font-bold px-3 pt-3 leading-relaxed" style={{ color: C.green }}>
              {kicker}
            </p>
          )}
          <div className="flex-1 min-h-0 overflow-hidden">
            {children}
          </div>
        </>
      )}
    </section>
  )
}