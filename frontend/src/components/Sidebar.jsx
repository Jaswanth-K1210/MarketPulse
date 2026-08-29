import React from 'react'
import { LayoutDashboard, Search, Bell, Star, TrendingUp, Settings, Globe, BarChart2, PieChart } from 'lucide-react'

const C = {
  bg:     '#090e1b',
  active: 'rgba(59,130,246,0.14)',
  border: '#141f33',
  text:   '#c8d6ee',
  muted:  '#4a6080',
  blue:   '#4f91f6',
}

const nav = [
  { id: 'dashboard', label: 'Dashboard',        icon: LayoutDashboard },
  { id: 'search',    label: 'Company Search',    icon: Search },
  { id: 'company',   label: 'Company Deep Dive', icon: BarChart2 },
  { id: 'alerts',    label: 'Alerts',            icon: Bell },
  { id: 'watchlist', label: 'Watchlist',         icon: Star },
  { id: 'trends',    label: 'Market Trends',     icon: TrendingUp },
  { id: 'settings',  label: 'Settings',          icon: Settings },
]

export default function Sidebar({ activeTab, setActiveTab }) {
  const user = localStorage.getItem('marketpulse_user') || 'User'

  return (
    <div className="flex flex-col shrink-0 border-r" style={{ width: 200, background: C.bg, borderColor: C.border }}>

      {/* Brand */}
      <div className="px-4 py-5 border-b" style={{ borderColor: C.border }}>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-black shrink-0"
            style={{ background: 'linear-gradient(135deg,#2563eb,#7c3aed)', color: '#fff' }}>
            ⚡
          </div>
          <div>
            <div className="text-[13px] font-black tracking-wide leading-none" style={{ color: C.text }}>
              MarketPulse
            </div>
            <div className="text-[9px] uppercase tracking-widest mt-0.5" style={{ color: C.muted }}>
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
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all group"
              style={{
                background: active ? C.active : 'transparent',
                border: `1px solid ${active ? 'rgba(59,130,246,0.22)' : 'transparent'}`,
              }}>
              <Icon size={15}
                style={{ color: active ? C.blue : C.muted, strokeWidth: active ? 2.2 : 1.8 }}
                className="shrink-0 transition-colors group-hover:text-slate-300" />
              <span className="text-[12px] font-semibold transition-colors"
                style={{ color: active ? C.text : C.muted }}
                onMouseEnter={e => { if (!active) e.target.style.color = '#94a3b8' }}
                onMouseLeave={e => { if (!active) e.target.style.color = C.muted }}>
                {label}
              </span>
              {id === 'alerts' && (
                <span className="ml-auto text-[9px] font-black px-1.5 py-0.5 rounded-full"
                  style={{ background: 'rgba(239,68,68,0.15)', color: '#f87171' }}>
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
          <div className="w-7 h-7 rounded-lg flex items-center justify-center text-[11px] font-black shrink-0"
            style={{ background: 'linear-gradient(135deg,#1e40af,#4c1d95)', color: '#93c5fd' }}>
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
