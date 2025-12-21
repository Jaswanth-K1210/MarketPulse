
import React, { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Search from './pages/Search'
import Watchlist from './pages/Watchlist'
import Alerts from './pages/Alerts'
import Trends from './pages/Trends'
import Settings from './pages/Settings'
import './App.css'

function App() {
  const [user, setUser] = useState(null)
  const [activeTab, setActiveTab] = useState('dashboard')
  const [showTriggerModal, setShowTriggerModal] = useState(false)

  useEffect(() => {
    // Check for existing session
    const savedUser = localStorage.getItem('marketpulse_user')
    if (savedUser) setUser(savedUser)

    // Apply theme
    const savedTheme = localStorage.getItem('mp_theme') || 'dark'
    document.documentElement.setAttribute('data-theme', savedTheme)
  }, [])

  if (!user) {
    return <Login onLogin={setUser} />
  }

  return (
    <div className="flex h-screen bg-dark text-primary">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      <main className="flex-1 overflow-auto bg-gradient-to-br from-dark to-darkBg">
        {activeTab === 'dashboard' && <Dashboard onTrigger={() => setShowTriggerModal(true)} />}
        {activeTab === 'search' && <Search />}
        {activeTab === 'watchlist' && <Watchlist />}
        {activeTab === 'alerts' && <Alerts />}
        {activeTab === 'trends' && <Trends />}
        {activeTab === 'settings' && <Settings onLogout={() => { localStorage.removeItem('marketpulse_user'); setUser(null); }} />}
      </main>
    </div>
  )
}

export default App
