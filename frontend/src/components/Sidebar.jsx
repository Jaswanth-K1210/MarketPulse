
import React from 'react'
import { LayoutDashboard, Search, Bell, Star, TrendingUp, Settings } from 'lucide-react'

export default function Sidebar({ activeTab, setActiveTab }) {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'search', label: 'Company Search', icon: Search },
    { id: 'alerts', label: 'Alerts', icon: Bell },
    { id: 'watchlist', label: 'Watchlist', icon: Star },
    { id: 'trends', label: 'Market Trends', icon: TrendingUp },
    { id: 'settings', label: 'Settings', icon: Settings },
  ]

  const userName = localStorage.getItem('marketpulse_user') || 'Protocol User';

  return (
    <div className="w-72 bg-darkBg border-r border-darkBorder flex flex-col relative z-50 transition-colors">
      {/* Header */}
      <div className="p-8">
        <div className="flex items-center gap-3 mb-1 group cursor-default">
          <div className="w-10 h-10 bg-gradient-to-tr from-blue-600 to-purple-600 rounded-xl flex items-center justify-center text-white font-black shadow-lg shadow-blue-500/20 group-hover:rotate-12 transition-transform duration-300">⚡</div>
          <div>
            <h1 className="font-black text-xl tracking-tighter uppercase italic text-primary">MarketPulse</h1>
            <div className="flex items-center gap-1.5">
              <span className="w-1 h-1 bg-blue-500 rounded-full animate-pulse"></span>
              <p className="text-[10px] text-secondary font-bold uppercase tracking-widest leading-none">Intelligence Hub</p>
            </div>
          </div>
        </div>
      </div>

      {/* Menu */}
      <nav className="flex-1 px-4 space-y-1">
        {menuItems.map(item => {
          const Icon = item.icon
          const isActive = activeTab === item.id
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-4 px-4 py-3.5 rounded-2xl transition-all duration-300 group ${isActive
                ? 'bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-lg shadow-blue-600/20'
                : 'text-secondary hover:text-primary hover:bg-white/5'
                }`}
            >
              <div className={`transition-transform duration-300 ${isActive ? 'scale-110' : 'group-hover:scale-110'}`}>
                <Icon size={22} strokeWidth={isActive ? 2.5 : 2} />
              </div>
              <span className={`text-sm font-bold tracking-tight ${isActive ? 'text-white' : 'text-secondary group-hover:text-primary'}`}>
                {item.label}
              </span>
              {isActive && (
                <div className="ml-auto w-1.5 h-1.5 bg-white rounded-full shadow-[0_0_8px_white]"></div>
              )}
            </button>
          )
        })}
      </nav>

      {/* Footer - User Info */}
      <div className="p-6">
        <div className="p-4 rounded-2xl bg-white/5 border border-white/5 flex items-center gap-4 group hover:bg-white/10 transition-colors cursor-pointer">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-gray-700 to-gray-800 flex items-center justify-center text-gray-300 font-black text-lg border border-white/10 shadow-inner">
            {userName.charAt(0).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-black text-primary truncate tracking-tight">{userName}</p>
            <p className="text-[10px] text-secondary font-bold uppercase tracking-tighter">Verified Agent</p>
          </div>
        </div>
      </div>
    </div>
  )
}
