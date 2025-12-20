import React, { useState } from 'react'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import './App.css'

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [showTriggerModal, setShowTriggerModal] = useState(false)

  return (
    <div className="flex h-screen bg-dark text-white">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      <main className="flex-1 overflow-auto">
        {activeTab === 'dashboard' && <Dashboard onTrigger={() => setShowTriggerModal(true)} />}
      </main>
    </div>
  )
}

export default App
