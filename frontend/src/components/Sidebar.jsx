import React from 'react'
import { LayoutDashboard, Bell, TrendingUp, Settings, BarChart2 } from 'lucide-react'

const C = {
  bg:     '#0d0d0d',
  active: 'rgba(74,222,128,0.08)',
  border: '#2a2a2a',
  borderDim: '#1c1c1c',
  text:   '#f5f5f5',
  muted:  '#9ca3af',
  blue:   '#4ade80',
}

const nav = [
  { id: 'dashboard', label: 'Dashboard',     icon: LayoutDashboard },
  { id: 'research',  label: 'Research',      icon: BarChart2 },
  { id: 'trends',    label: 'Market',        icon: TrendingUp },
  { id: 'alerts',    label: 'Alerts',        icon: Bell },
  { id: 'settings',  label: 'Settings',      icon: Settings },
]

export default function Sidebar({ activeTab, setActiveTab }) {
  const user = localStorage.getItem('marketpulse_user') || 'User'

  return (
    <div className="flex flex-col shrink-0 border-r" style={{ width: 200, background: C.bg, borderColor: C.border }}>

      {/* Brand */}
      <div className="px-4 py-5 border-b" style={{ borderColor: C.border }}>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-none flex items-center justify-center text-sm font-semibold shrink-0"
            style={{ background: '#14532d', border: '1px solid #4ade80', color: '#4ade80' }}>
            ⚡
          </div>
          <div>
            <div className="text-[13px] font-semibold leading-none tracking-tight" style={{ color: C.text }}>
              MarketPulse
            </div>
            <div className="text-[9px] mt-0.5" style={{ color: C.muted }}>
              AI Intelligence
            </div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 space-y-0.5">
        {nav.map(({ id, label, icon: Icon }) => {
          const active = activeTab === id
          return (
            <button key={id} onClick={() => setActiveTab(id)}
              className="w-full flex items-center gap-3 px-3 py-2 rounded text-left transition-all group"
              style={{
                background: active ? C.active : 'transparent',
                border: `1px solid ${active ? 'rgba(74,222,128,0.22)' : 'transparent'}`,
              }}>
              <Icon size={15}
                style={{ color: active ? C.blue : C.muted, strokeWidth: active ? 2.2 : 1.8 }}
                className="shrink-0 transition-colors group-hover:text-gray-300" />
              <span className="text-[12px] font-semibold transition-colors"
                style={{ color: active ? C.text : C.muted }}
                onMouseEnter={e => { if (!active) e.target.style.color = '#d4d4d4' }}
                onMouseLeave={e => { if (!active) e.target.style.color = C.muted }}>
                {label}
              </span>
              {id === 'alerts' && (
                <span className="ml-auto text-[9px] font-semibold px-1.5 py-0.5 rounded-full"
                  style={{ background: 'rgba(248,113,113,0.12)', color: '#f87171' }}>
                  •
                </span>
              )}
            </button>
          )
        })}
      </nav>

      {/* User */}
      <div className="px-3 py-3 border-t" style={{ borderColor: C.border }}>
        <div className="flex items-center gap-2.5 px-1">
          <div className="w-7 h-7 rounded-none flex items-center justify-center text-[11px] font-semibold shrink-0"
            style={{ background: '#14532d', border: '1px solid rgba(74,222,128,0.4)', color: '#86efac' }}>
            {user.charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0">
            <div className="text-[11px] font-semibold truncate" style={{ color: C.text }}>{user}</div>
            <div className="text-[9px] truncate" style={{ color: C.muted }}>Portfolio Manager</div>
          </div>
        </div>
      </div>
    </div>
  )
}
