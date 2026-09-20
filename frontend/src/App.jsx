
import React, { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Research from './pages/Research'
import Alerts from './pages/Alerts'
import Trends from './pages/Trends'
import Settings from './pages/Settings'
import './App.css'
import DisclaimerBanner from './components/DisclaimerBanner'
import BackendStatus from './components/BackendStatus'
import ErrorBoundary from './components/ErrorBoundary'

function App() {
  const [user, setUser] = useState(null)
  const [activeTab, setActiveTab] = useState('dashboard')
  const [companyTicker, setCompanyTicker] = useState(null)

  useEffect(() => {
    const savedUser = localStorage.getItem('marketpulse_user')
    if (savedUser) setUser(savedUser)
    const savedTheme = localStorage.getItem('mp_theme') || 'dark'
    document.documentElement.setAttribute('data-theme', savedTheme)
  }, [])

  const handleCompanySearch = (ticker) => {
    setCompanyTicker(ticker)
    setActiveTab('research')
  }

  if (!user) {
    return <Login onLogin={setUser} />
  }

  return (
    <div className="flex h-screen text-primary overflow-hidden" style={{ background: '#0a0a0a' }}>
      <Sidebar activeTab={activeTab} setActiveTab={(tab) => { setActiveTab(tab); if (tab !== 'research') setCompanyTicker(null) }} />
      <main className="flex-1 overflow-hidden flex flex-col" style={{ background: '#0a0a0a' }}>
        <BackendStatus />
        {activeTab === 'dashboard' && <ErrorBoundary label="Dashboard"><Dashboard onCompanyClick={handleCompanySearch} /></ErrorBoundary>}
        {activeTab === 'research' && <div className="flex-1 overflow-auto"><ErrorBoundary label="Research"><Research initialTicker={companyTicker} /></ErrorBoundary></div>}
        {activeTab === 'alerts' && <div className="flex-1 overflow-auto"><ErrorBoundary label="Alerts"><Alerts /></ErrorBoundary></div>}
        {activeTab === 'trends' && <div className="flex-1 overflow-auto"><ErrorBoundary label="Market"><Trends /></ErrorBoundary></div>}
        {activeTab === 'settings' && <div className="flex-1 overflow-auto"><ErrorBoundary label="Settings"><Settings onLogout={() => { localStorage.removeItem('marketpulse_user'); setUser(null); }} /></ErrorBoundary></div>}
        <DisclaimerBanner />
      </main>
    </div>
  )
}

export default App
