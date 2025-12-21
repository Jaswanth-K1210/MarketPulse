
import React, { useState } from 'react'
import { ArrowRight, Loader, Plus, Trash2, Zap } from 'lucide-react'

import TerminalLoader from '../components/TerminalLoader'

export default function Login({ onLogin }) {
    const [step, setStep] = useState(1)
    const [showLoader, setShowLoader] = useState(false)
    const [formData, setFormData] = useState({
        name: '',
        tickers: []
    })
    const [currentTicker, setCurrentTicker] = useState('')
    const [loading, setLoading] = useState(false)

    const handleNext = (e) => {
        if (e) e.preventDefault()
        if (formData.name.trim()) {
            setStep(2)
        }
    }

    const addTicker = (e) => {
        if (e) e.preventDefault()
        const ticker = currentTicker.trim().toUpperCase()
        if (ticker && !formData.tickers.includes(ticker)) {
            setFormData(prev => ({
                ...prev,
                tickers: [...prev.tickers, ticker]
            }))
            setCurrentTicker('')
        }
    }

    const removeTicker = (ticker) => {
        setFormData(prev => ({
            ...prev,
            tickers: prev.tickers.filter(t => t !== ticker)
        }))
    }

    const [userName, setUserName] = useState('')

    const handleSubmit = async () => {
        const name = formData.name.trim() || 'User'
        setLoading(true)

        try {
            // 1. Save User Session Locally First (Optimistic)
            localStorage.setItem('marketpulse_user', name)
            localStorage.setItem('marketpulse_portfolio', JSON.stringify(formData.tickers))

            // 2. Build Portfolio Object
            const portfolioPayload = {
                user_name: name,
                portfolio: formData.tickers.map(ticker => ({
                    company: ticker,
                    ticker: ticker,
                    quantity: 10,
                    purchase_price: 100.00
                }))
            }

            // 3. Attempt to Sync with Backend (Don't let failures block login)
            try {
                const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
                const portfolioResponse = await fetch(`${apiUrl}/api/portfolio`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(portfolioPayload)
                })

                const portfolioData = await portfolioResponse.json()

                // Save auth token if provided
                if (portfolioData.token) {
                    localStorage.setItem('marketpulse_token', portfolioData.token)
                    localStorage.setItem('marketpulse_user_id', portfolioData.user_id)
                }

                const watchlistPromises = formData.tickers.map(ticker =>
                    fetch(`${apiUrl}/api/watchlist`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ticker })
                    })
                )
                await Promise.all(watchlistPromises).catch(e => console.warn('Watchlist sync error:', e))
            } catch (syncErr) {
                console.warn('Backend sync failed, proceeding with local session:', syncErr)
            }

            // 4. Trigger Agent Discovery Workflow in Background
            if (formData.tickers.length > 0) {
                fetch(`${apiUrl}/api/run-intelligence`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: name,
                        portfolio: formData.tickers
                    })
                }).catch(e => console.warn('Workflow trigger failed:', e))
            }

            // 5. Show Loader instead of immediately logging in
            setUserName(name) // Store for callback
            setLoading(false)
            setShowLoader(true)
            // onLogin(name) will be called by TerminalLoader onComplete

        } catch (err) {
            console.error('Login error:', err)
            // If critical error, just login
            onLogin(name)
        }
    }

    if (showLoader) {
        return <TerminalLoader onComplete={() => {
            console.log('TerminalLoader complete, calling onLogin with:', userName)
            onLogin(userName || 'User')
        }} />
    }

    return (
        <div className="min-h-screen bg-darkBg flex items-center justify-center p-4 relative overflow-hidden">
            {/* Background Decorative Elements */}
            <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-blue-600/10 blur-[120px] rounded-full animate-pulse"></div>
            <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-purple-600/10 blur-[120px] rounded-full animate-pulse-slow"></div>

            <div className="max-w-xl w-full glass-card border border-white/5 rounded-[2.5rem] p-10 shadow-2xl relative z-10 animate-fade-in">
                {/* Header */}
                <div className="text-center mb-10">
                    <div className="w-20 h-20 bg-gradient-to-tr from-blue-600 to-purple-600 rounded-3xl flex items-center justify-center text-white text-4xl font-black mx-auto mb-6 shadow-2xl shadow-blue-500/20 rotate-3 animate-bounce-slow">
                        ⚡
                    </div>
                    <h1 className="text-4xl font-black text-primary mb-2 tracking-tighter uppercase italic">MarketPulse</h1>
                    <p className="text-secondary text-sm font-medium tracking-wide uppercase opacity-60">AI Market Intelligence Hub</p>
                </div>

                {/* Step 1: User Name */}
                {step === 1 && (
                    <form onSubmit={handleNext} className="space-y-8 animate-fade-in">
                        <div className="text-center">
                            <h2 className="text-xl font-black text-primary uppercase tracking-tight">Identity Setup</h2>
                            <p className="text-xs text-secondary mt-1">Tell us your name to begin analysis</p>
                        </div>
                        <div>
                            <input
                                type="text"
                                required
                                autoFocus
                                className="w-full px-8 py-6 bg-dark/40 border-2 border-white/10 rounded-3xl text-center text-2xl text-primary placeholder-secondary/50 focus:outline-none focus:border-blue-500 transition-all font-black"
                                placeholder="YOUR NAME"
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            />
                        </div>
                        <button
                            type="submit"
                            className="w-full py-5 px-6 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-black rounded-3xl transition-all flex items-center justify-center gap-3 shadow-xl shadow-blue-600/20 active:scale-95 group uppercase tracking-widest"
                        >
                            Continue to Assets
                            <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
                        </button>
                    </form>
                )}

                {/* Step 2: Portfolio Setup */}
                {step === 2 && (
                    <div className="space-y-8 animate-fade-in">
                        <div className="text-center">
                            <h2 className="text-xl font-black text-primary uppercase tracking-tight">Sync Your Watchlist</h2>
                            <p className="text-xs text-secondary mt-1">Which companies should the AI monitor for <b>{formData.name}</b>?</p>
                            <div className="mt-4 p-3 bg-black/40 border border-yellow-500/30 rounded-xl">
                                <p className="text-xs text-yellow-300 font-medium">
                                    📝 <b>Note:</b> Please add only <span className="text-yellow-400 font-black">US stock companies</span> and enter ticker name only.
                                </p>
                                <p className="text-[10px] text-gray-400 mt-1">
                                    Example: <span className="text-blue-400 font-mono">Apple → AAPL</span>,
                                    <span className="text-blue-400 font-mono ml-2">Tesla → TSLA</span>
                                </p>
                            </div>
                        </div>

                        <form onSubmit={addTicker} className="flex gap-4">
                            <input
                                type="text"
                                className="flex-1 px-6 py-4 bg-black/60 border-2 border-white/20 rounded-2xl text-primary placeholder-secondary/50 focus:outline-none focus:border-blue-500/50 font-black tracking-widest text-xl"
                                placeholder="ENTER TICKER"
                                value={currentTicker}
                                onChange={(e) => setCurrentTicker(e.target.value.toUpperCase())}
                            />
                            <button
                                type="submit"
                                disabled={!currentTicker.trim()}
                                className="bg-blue-600 hover:bg-blue-500 px-6 rounded-2xl disabled:opacity-30 border border-white/5 transition-all active:scale-90 shadow-lg shadow-blue-500/20"
                            >
                                <Plus size={28} className="text-white" />
                            </button>
                        </form>

                        <div className="min-h-[160px] bg-dark/20 rounded-3xl p-6 flex flex-wrap content-start gap-3 border border-white/5 border-dashed">
                            {formData.tickers.length === 0 && (
                                <div className="w-full h-full flex flex-col items-center justify-center text-secondary text-[10px] font-black uppercase tracking-widest italic opacity-40 py-10">
                                    <div className="w-10 h-10 bg-white/5 rounded-full flex items-center justify-center mb-3">?</div>
                                    No Companies Added Yet
                                </div>
                            )}
                            {formData.tickers.map(ticker => (
                                <span key={ticker} className="bg-blue-500/10 text-blue-400 border border-blue-500/20 px-5 py-3 rounded-2xl text-sm font-black tracking-widest flex items-center gap-3 group animate-scale-in">
                                    {ticker}
                                    <button onClick={() => removeTicker(ticker)} className="text-gray-500 hover:text-red-400 transition-colors"><Trash2 size={14} /></button>
                                </span>
                            ))}
                        </div>

                        <div className="flex gap-4">
                            <button
                                onClick={() => setStep(1)}
                                className="px-6 py-5 bg-white/5 hover:bg-white/10 text-secondary font-black rounded-3xl transition-all active:scale-95"
                            >
                                Back
                            </button>
                            <button
                                onClick={handleSubmit}
                                disabled={loading}
                                className={`flex-1 py-5 px-6 bg-gradient-to-r ${formData.tickers.length === 0 ? 'from-gray-700 to-gray-600' : 'from-green-600 to-green-500'} hover:opacity-90 text-white font-black rounded-3xl shadow-xl transition-all flex items-center justify-center gap-3 active:scale-95 disabled:opacity-50 uppercase tracking-widest`}
                            >
                                {loading ? (
                                    <Loader className="animate-spin" size={20} />
                                ) : (
                                    <>
                                        <span>{formData.tickers.length === 0 ? 'Skip & Launch' : 'Launch Dashboard'}</span>
                                        <Zap size={20} fill="currentColor" />
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
