
import React, { useState } from 'react'
import { Bell, Shield, User, Globe, Moon, LogOut, Check } from 'lucide-react'

export default function Settings({ onLogout }) {
    const [notifications, setNotifications] = useState(true)
    const [theme, setTheme] = useState(localStorage.getItem('mp_theme') || 'dark')

    const changeTheme = (newTheme) => {
        setTheme(newTheme)
        localStorage.setItem('mp_theme', newTheme)
        document.documentElement.setAttribute('data-theme', newTheme)
    }

    return (
        <div className="p-8 max-w-4xl animate-fade-in">
            <h2 className="text-3xl font-bold mb-8 text-gradient">Settings</h2>

            <div className="space-y-6">
                {/* Profile Section */}
                <div className="bg-darkBg/50 backdrop-blur-md border border-darkBorder rounded-2xl p-6 shadow-xl hover:shadow-2xl transition-all">
                    <div className="flex items-center gap-6 mb-8">
                        <div className="w-20 h-20 bg-gradient-to-tr from-blue-600 to-purple-600 rounded-full flex items-center justify-center text-3xl font-bold text-white shadow-lg shadow-blue-500/20">
                            {localStorage.getItem('marketpulse_user')?.charAt(0).toUpperCase() || 'U'}
                        </div>
                        <div>
                            <h3 className="text-2xl font-bold">{localStorage.getItem('marketpulse_user') || 'User'}</h3>
                            <p className="text-blue-400 font-medium tracking-wide prose-sm">@{localStorage.getItem('marketpulse_user')?.toLowerCase().replace(/\s/g, '') || 'user'}</p>
                        </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="bg-dark/40 p-4 rounded-xl flex items-center gap-4 border border-white/5 group hover:bg-dark/60 transition-colors">
                            <div className="p-2 bg-blue-500/10 rounded-lg group-hover:scale-110 transition-transform">
                                <User className="text-blue-500" size={20} />
                            </div>
                            <div>
                                <div className="text-xs text-gray-500 uppercase font-bold tracking-tighter">Account Type</div>
                                <div className="font-semibold">Pro Plan</div>
                            </div>
                        </div>
                        <div className="bg-dark/40 p-4 rounded-xl flex items-center gap-4 border border-white/5 group hover:bg-dark/60 transition-colors">
                            <div className="p-2 bg-green-500/10 rounded-lg group-hover:scale-110 transition-transform">
                                <Shield className="text-green-500" size={20} />
                            </div>
                            <div>
                                <div className="text-xs text-gray-500 uppercase font-bold tracking-tighter">Security Status</div>
                                <div className="font-semibold">Secured</div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Theme Section */}
                <div className="bg-darkBg/50 backdrop-blur-md border border-darkBorder rounded-2xl p-6 shadow-xl">
                    <h3 className="font-bold mb-6 flex items-center gap-2 text-lg">
                        <Moon size={20} className="text-purple-400" /> Interface Appearance
                    </h3>
                    <div className="grid grid-cols-3 gap-4">
                        {[
                            { id: 'dark', label: 'Dark', color: 'bg-[#0F1419]' },
                            { id: 'light', label: 'Light', color: 'bg-white' },
                            { id: 'grey', label: 'Grey', color: 'bg-[#2D3436]' }
                        ].map(t => (
                            <button
                                key={t.id}
                                onClick={() => changeTheme(t.id)}
                                className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${theme === t.id ? 'border-blue-500 bg-blue-500/5' : 'border-transparent bg-dark/40 hover:bg-dark/60'
                                    }`}
                            >
                                <div className={`w-12 h-12 rounded-lg shadow-inner ${t.color}`} />
                                <span className="text-sm font-medium">{t.label}</span>
                                {theme === t.id && <Check size={14} className="text-blue-500" />}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Preferences */}
                <div className="bg-darkBg/50 backdrop-blur-md border border-darkBorder rounded-2xl p-6 shadow-xl">
                    <h3 className="font-bold mb-4 flex items-center gap-2 text-lg">
                        <Globe size={20} className="text-blue-400" /> App Preferences
                    </h3>
                    <div className="space-y-4">
                        <div className="flex items-center justify-between p-4 bg-dark/40 rounded-xl border border-white/5 hover:bg-dark/60 transition-colors">
                            <div className="flex items-center gap-4">
                                <div className="p-2 bg-yellow-500/10 rounded-lg">
                                    <Bell className="text-yellow-500" size={20} />
                                </div>
                                <div>
                                    <div className="font-medium">Real-time Risk Alerts</div>
                                    <div className="text-xs text-gray-500">Get notified of portfolio impacts</div>
                                </div>
                            </div>
                            <button
                                onClick={() => setNotifications(!notifications)}
                                className={`w-12 h-6 rounded-full transition-all relative ${notifications ? 'bg-blue-600 shadow-[0_0_10px_rgba(37,99,235,0.4)]' : 'bg-gray-600'}`}
                            >
                                <div className={`absolute top-1 left-1 bg-white w-4 h-4 rounded-full transition-all duration-300 ${notifications ? 'translate-x-6' : ''}`} />
                            </button>
                        </div>
                    </div>
                </div>

                {/* Danger Zone */}
                <div className="bg-red-500/5 border border-red-500/20 rounded-2xl p-6 shadow-xl">
                    <h3 className="font-bold text-red-500 mb-2 flex items-center gap-2">
                        <LogOut size={18} /> Account Management
                    </h3>
                    <p className="text-sm text-gray-400 mb-6 font-medium">Clear session data and sign out securely.</p>
                    <button
                        onClick={onLogout}
                        className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-red-600/90 hover:bg-red-600 text-white rounded-xl transition-all font-bold shadow-lg shadow-red-600/20 active:scale-95"
                    >
                        Sign Out
                    </button>
                </div>
            </div>
        </div>
    )
}

