
import React, { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Search from './pages/Search'
import Watchlist from './pages/Watchlist'
import Alerts from './pages/Alerts'
import Trends from './pages/Trends'
import Settings from './pages/Settings'
import CompanyDetail from './pages/CompanyDetail'
import './App.css'

function App() {
  const [user, setUser] = useState(null)
  const [activeTab, setActiveTab] = useState('dashboard')
  const [showTriggerModal, setShowTriggerModal] = useState(false)
  const [companyTicker, setCompanyTicker] = useState(null)

  useEffect(() => {
    const savedUser = localStorage.getItem('marketpulse_user')
    if (savedUser) setUser(savedUser)
    const savedTheme = localStorage.getItem('mp_theme') || 'dark'
    document.documentElement.setAttribute('data-theme', savedTheme)
  }, [])

  const handleCompanySearch = (ticker) => {
    setCompanyTicker(ticker)
    setActiveTab('company')
  }

  if (!user) {
    return <Login onLogin={setUser} />
  }

  return (
    <div className="flex h-screen text-primary overflow-hidden" style={{ background: '#0b1221' }}>
      <Sidebar activeTab={activeTab} setActiveTab={(tab) => { setActiveTab(tab); if (tab !== 'company') setCompanyTicker(null) }} />
      <main className="flex-1 overflow-hidden flex flex-col" style={{ background: '#0b1221' }}>
        {activeTab === 'dashboard' && <Dashboard onTrigger={() => setShowTriggerModal(true)} onCompanyClick={handleCompanySearch} />}
        {activeTab === 'search' && <div className="flex-1 overflow-auto"><Search onCompanyClick={handleCompanySearch} /></div>}
        {activeTab === 'company' && <CompanyDetail ticker={companyTicker} onBack={() => setActiveTab('dashboard')} />}
        {activeTab === 'watchlist' && <div className="flex-1 overflow-auto"><Watchlist onCompanyClick={handleCompanySearch} /></div>}
        {activeTab === 'alerts' && <div className="flex-1 overflow-auto"><Alerts /></div>}
        {activeTab === 'trends' && <div className="flex-1 overflow-auto"><Trends /></div>}
        {activeTab === 'settings' && <div className="flex-1 overflow-auto"><Settings onLogout={() => { localStorage.removeItem('marketpulse_user'); setUser(null); }} /></div>}
      </main>
    </div>
  )
}

export default App
