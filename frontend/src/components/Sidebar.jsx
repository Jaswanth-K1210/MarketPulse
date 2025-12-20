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

  return (
    <div className="w-64 bg-darkBg border-r border-darkBorder flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-darkBorder">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center text-white font-bold">⚡</div>
          <div>
            <h1 className="font-bold text-lg">MarketPulse</h1>
            <p className="text-xs text-gray-400">AI Intelligence</p>
          </div>
        </div>
      </div>

      {/* Menu */}
      <nav className="flex-1 p-4 space-y-2">
        {menuItems.map(item => {
          const Icon = item.icon
          const isActive = activeTab === item.id
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                isActive
                  ? 'bg-blue-500 text-white'
                  : 'text-gray-300 hover:bg-darkBorder hover:text-white'
              }`}
            >
              <Icon size={20} />
              <span>{item.label}</span>
            </button>
          )
        })}
      </nav>

      {/* Footer - User Info */}
      <div className="p-4 border-t border-darkBorder">
        <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-darkBorder">
          <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white font-bold text-sm">
            JD
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">John Doe</p>
            <p className="text-xs text-gray-400 truncate">Portfolio Manager</p>
          </div>
        </div>
      </div>
    </div>
  )
}
