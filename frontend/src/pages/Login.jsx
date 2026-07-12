import React, { useState } from 'react'
import { ArrowRight, Loader, Plus, Trash2, Zap, Eye, EyeOff, Shield, Activity } from 'lucide-react'
import { useGoogleLogin } from '@react-oauth/google'
import TerminalLoader from '../components/TerminalLoader'
import { authLogin, authRegister, authGoogle } from '../services/api'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const GOOGLE_ENABLED = !!import.meta.env.VITE_GOOGLE_CLIENT_ID

export default function Login({ onLogin }) {
  const [step, setStep] = useState(1)
  const [isNewUser, setIsNewUser] = useState(false)
  const [showLoader, setShowLoader] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [formData, setFormData] = useState({ username: '', password: '', email: '', confirmPassword: '', tickers: [] })
  const [currentTicker, setCurrentTicker] = useState('')
  const [loading, setLoading] = useState(false)
  const [googleLoading, setGoogleLoading] = useState(false)
  const [error, setError] = useState('')
  const [savedUsername, setSavedUsername] = useState('')
  const [pendingGoogleAuth, setPendingGoogleAuth] = useState(null)

  // ── Helpers ──────────────────────────────────────────────────────────────

  const persistSession = (token, user, tickers) => {
    localStorage.setItem('marketpulse_token', token)
    localStorage.setItem('marketpulse_user', user.username)
    localStorage.setItem('marketpulse_user_id', String(user.id))
    localStorage.setItem('marketpulse_portfolio', JSON.stringify(tickers))
  }

  const syncPortfolio = async (token, username, tickers) => {
    if (!tickers.length) return
    const payload = {
      user_name: username,
      portfolio: tickers.map(ticker => ({ company: ticker, ticker, quantity: 10, purchase_price: 100 })),
    }
    await fetch(`${API_BASE_URL}/api/portfolio`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload),
    }).catch(() => {})
    await Promise.all(tickers.map(ticker =>
      fetch(`${API_BASE_URL}/api/watchlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ ticker }),
      }).catch(() => {})
    ))
    fetch(`${API_BASE_URL}/api/run-intelligence`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ user_id: username, portfolio: tickers }),
    }).catch(() => {})
  }

  const launch = (username) => {
    setSavedUsername(username)
    setLoading(false)
    setGoogleLoading(false)
    setShowLoader(true)
  }

  // ── Google OAuth flow ────────────────────────────────────────────────────

  const googleLogin = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      setGoogleLoading(true)
      setError('')
      try {
        const userInfo = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
          headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
        }).then(r => r.json())

        const data = await authGoogle(tokenResponse.access_token)
        setGoogleLoading(false)
        setPendingGoogleAuth({ token: data.token, user: data.user })
        setFormData(prev => ({ ...prev, username: data.user.username }))
        setStep(2)
      } catch (err) {
        setGoogleLoading(false)
        setError('Google sign-in failed. Try username/password instead.')
      }
    },
    onError: () => {
      setGoogleLoading(false)
      setError('Google sign-in was cancelled or failed.')
    },
    flow: 'implicit',
  })

  // ── Username/password flow ───────────────────────────────────────────────

  const handleNext = (e) => {
    if (e) e.preventDefault()
    setError('')
    if (!formData.username.trim() || !formData.password.trim()) return
    if (isNewUser) {
      if (!formData.email.trim()) {
        setError('Email is required to create an account.')
        return
      }
      if (formData.password.length < 6) {
        setError('Password must be at least 6 characters.')
        return
      }
      if (formData.password !== formData.confirmPassword) {
        setError('Passwords do not match.')
        return
      }
    }
    setStep(2)
  }

  const addTicker = (e) => {
    if (e) e.preventDefault()
    const ticker = currentTicker.trim().toUpperCase()
    if (ticker && !formData.tickers.includes(ticker)) {
      setFormData(prev => ({ ...prev, tickers: [...prev.tickers, ticker] }))
      setCurrentTicker('')
    }
  }

  const removeTicker = (ticker) => {
    setFormData(prev => ({ ...prev, tickers: prev.tickers.filter(t => t !== ticker) }))
  }

  const handleSubmit = async () => {
    setLoading(true)
    setError('')
    try {
      if (pendingGoogleAuth) {
        const { token, user } = pendingGoogleAuth
        persistSession(token, user, formData.tickers)
        await syncPortfolio(token, user.username, formData.tickers)
        launch(user.username)
        return
      }
      const data = isNewUser
        ? await authRegister(formData.username, formData.password, formData.email || null)
        : await authLogin(formData.username, formData.password)
      persistSession(data.token, data.user, formData.tickers)
      await syncPortfolio(data.token, data.user.username, formData.tickers)
      launch(data.user.username)
    } catch (err) {
      setLoading(false)
      const msg = err.message || ''
      if (msg.includes('409') || msg.toLowerCase().includes('already') || msg.toLowerCase().includes('taken')) {
        setError('Username already taken — try signing in instead.')
        setIsNewUser(false)
      } else if (msg.includes('401') || msg.toLowerCase().includes('invalid')) {
        setError('Wrong username or password.')
      } else {
        const name = formData.username
        localStorage.setItem('marketpulse_user', name)
        localStorage.setItem('marketpulse_portfolio', JSON.stringify(formData.tickers))
        launch(name)
      }
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────

  if (showLoader) {
    return <TerminalLoader onComplete={() => onLogin(savedUsername || 'User')} />
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden" style={{ background: '#020617' }}>
      {/* Dynamic Ambient Background Elements */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
        <div className="absolute -top-[20%] -left-[10%] w-[70vw] h-[70vw] bg-indigo-600/10 blur-[150px] rounded-full mix-blend-screen animate-pulse-slow"></div>
        <div className="absolute -bottom-[20%] -right-[10%] w-[60vw] h-[60vw] bg-cyan-600/10 blur-[150px] rounded-full mix-blend-screen animate-pulse-slow" style={{ animationDelay: '2s' }}></div>
        <div className="absolute top-[20%] right-[20%] w-[30vw] h-[30vw] bg-fuchsia-600/10 blur-[120px] rounded-full mix-blend-screen animate-pulse"></div>
        {/* Subtle grid pattern overlay */}
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxwYXRoIGQ9Ik0zNiAzNHYtNGgydjRoLTJ6bTAtOGgtMnY0aDJWMjZ6bS00IDRoLTJ2NGgydi00em0wLThoLTh2NGg4di00em0tMTAgNGgtMnY0aDJWMjJ6bS00LTRoLTR2NGg0di00em0tNiA0SDZ2NGg0VjI2em0tNCA0SDJ2NGg0di00em0wIDhoLTJ2NGg0di00em00IDRoLTR2NGg0di00em00IDRoLTR2NGg0di00em04IDRoLTh2NGg4di00em00IDRoLTR2NGg0di00em00IDRoLTR2NGg0di00em00IDRoLTR2NGg0di00em00IDRoLTR2NGg0di00em00LTRoLTR2NGg0di00em00LTRoLTR2NGg0di00em00LTRoLTR2NGg0di00em00LTRoLTR2NGg0di00eiIgZmlsbD0icmdiYSgyNTUsMjU1LDI1NSwwLjAyKSIgZmlsbC1vcGFjaXR5PSIxIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiLz48L2c+PC9zdmc+')] opacity-30 pointer-events-none"></div>
      </div>

      <div className="max-w-[480px] w-full relative z-10 animate-fade-in transition-all duration-500">
        <div className="bg-[#0b1021]/80 backdrop-blur-2xl border border-white/10 rounded-[2.5rem] p-10 shadow-[0_0_80px_-20px_rgba(79,70,229,0.25)] relative overflow-hidden">
          
          {/* Subtle top inner glow */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-[1px] bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent"></div>

          {/* Header */}
          <div className="text-center mb-10 relative">
            <div className="relative inline-block mb-6 group">
              <div className="absolute inset-0 bg-gradient-to-tr from-cyan-400 to-indigo-500 blur-xl opacity-40 group-hover:opacity-70 transition-opacity duration-500 animate-pulse"></div>
              <div className="relative w-20 h-20 bg-gradient-to-br from-[#0b1021] to-[#1a233a] border border-white/10 rounded-2xl flex items-center justify-center shadow-2xl transform rotate-3 group-hover:rotate-0 transition-transform duration-500">
                <Activity className="text-cyan-400 w-10 h-10 group-hover:scale-110 transition-transform duration-500" />
              </div>
            </div>
            <h1 className="text-4xl font-black mb-2 tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-blue-100 to-indigo-300">MarketPulse</h1>
            <p className="text-indigo-200/60 text-sm font-semibold tracking-widest uppercase">Intelligence Hub</p>
          </div>

          {/* ── STEP 1: AUTH ── */}
          {step === 1 && (
            <div className="space-y-7 animate-fade-in">
              <div className="text-center">
                <h2 className="text-2xl font-bold text-white tracking-tight">
                  {isNewUser ? 'Create Account' : 'Welcome Back'}
                </h2>
                <p className="text-sm text-indigo-200/50 mt-1.5 font-medium">
                  {isNewUser ? 'Join the future of market intelligence' : 'Enter your credentials to access the hub'}
                </p>
              </div>

              {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-2xl px-5 py-3.5 text-red-400 text-sm font-medium text-center flex items-center justify-center gap-2">
                  <Shield className="w-4 h-4" />
                  {error}
                </div>
              )}

              {/* Google OAuth button */}
              {GOOGLE_ENABLED && (
                <>
                  <button
                    type="button"
                    onClick={() => { setError(''); googleLogin() }}
                    disabled={googleLoading}
                    className="w-full py-4 px-6 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-semibold rounded-2xl transition-all duration-300 flex items-center justify-center gap-3 shadow-lg active:scale-[0.98] disabled:opacity-50"
                  >
                    {googleLoading ? (
                      <Loader className="animate-spin w-5 h-5" />
                    ) : (
                      <svg viewBox="0 0 24 24" className="w-5 h-5" xmlns="http://www.w3.org/2000/svg">
                        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                      </svg>
                    )}
                    Continue with Google
                  </button>

                  <div className="flex items-center gap-4 my-2">
                    <div className="flex-1 h-px bg-white/5" />
                    <span className="text-[10px] text-white/30 uppercase tracking-widest font-bold">or</span>
                    <div className="flex-1 h-px bg-white/5" />
                  </div>
                </>
              )}

              {/* Username / password form */}
              <form onSubmit={handleNext} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold text-indigo-200/60 uppercase tracking-widest ml-1">Username</label>
                  <input
                    type="text"
                    required
                    autoFocus
                    className="w-full px-5 py-4 bg-black/20 border border-white/10 rounded-2xl text-white placeholder-white/20 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 transition-all font-medium shadow-inner"
                    placeholder="Enter your username"
                    value={formData.username}
                    onChange={e => setFormData({ ...formData, username: e.target.value })}
                  />
                </div>

                {isNewUser && (
                  <div className="space-y-1.5">
                    <label className="text-[11px] font-bold text-indigo-200/60 uppercase tracking-widest ml-1">Email</label>
                    <input
                      type="email"
                      required
                      className="w-full px-5 py-4 bg-black/20 border border-white/10 rounded-2xl text-white placeholder-white/20 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 transition-all font-medium shadow-inner"
                      placeholder="your@email.com"
                      value={formData.email}
                      onChange={e => setFormData({ ...formData, email: e.target.value })}
                    />
                  </div>
                )}
                
                <div className="space-y-1.5 relative">
                  <label className="text-[11px] font-bold text-indigo-200/60 uppercase tracking-widest ml-1">Password</label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required
                      minLength={isNewUser ? 6 : 4}
                      className="w-full px-5 py-4 bg-black/20 border border-white/10 rounded-2xl text-white placeholder-white/20 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 transition-all font-medium pr-14 shadow-inner"
                      placeholder={isNewUser ? 'Create a password (min 6 chars)' : 'Enter your password'}
                      value={formData.password}
                      onChange={e => setFormData({ ...formData, password: e.target.value })}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(v => !v)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/80 transition-colors"
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>

                {isNewUser && (
                  <div className="space-y-1.5 relative">
                    <label className="text-[11px] font-bold text-indigo-200/60 uppercase tracking-widest ml-1">Confirm Password</label>
                    <input
                      type="password"
                      required
                      className="w-full px-5 py-4 bg-black/20 border border-white/10 rounded-2xl text-white placeholder-white/20 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 transition-all font-medium shadow-inner"
                      placeholder="Confirm your password"
                      value={formData.confirmPassword}
                      onChange={e => setFormData({ ...formData, confirmPassword: e.target.value })}
                    />
                  </div>
                )}
                
                <button
                  type="submit"
                  className="w-full py-4 mt-2 bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-500 hover:opacity-90 text-white font-bold rounded-2xl transition-all duration-300 flex items-center justify-center gap-3 shadow-[0_0_20px_rgba(99,102,241,0.4)] hover:shadow-[0_0_30px_rgba(99,102,241,0.6)] active:scale-[0.98]"
                >
                  {isNewUser ? 'Create Account' : 'Sign In'}
                  <ArrowRight size={18} />
                </button>
              </form>

              {!isNewUser && (
                <button
                  type="button"
                  onClick={() => { setIsNewUser(true); setError('') }}
                  className="w-full py-4 px-6 bg-gradient-to-r from-emerald-500/20 to-teal-500/20 hover:from-emerald-500/30 hover:to-teal-500/30 border border-emerald-500/30 text-emerald-300 font-bold rounded-2xl transition-all duration-300 flex items-center justify-center gap-3 active:scale-[0.98]"
                >
                  <Plus size={18} />
                  Create Account
                </button>
              )}
              <p className="text-center text-sm text-indigo-200/50 font-medium">
                {isNewUser ? 'Already have an account?' : ''}{' '}
                {isNewUser && (
                  <button
                    type="button"
                    onClick={() => { setIsNewUser(false); setError('') }}
                    className="text-cyan-400 hover:text-cyan-300 font-semibold transition-colors"
                  >
                    Sign in
                  </button>
                )}
              </p>
            </div>
          )}

          {/* ── STEP 2: PORTFOLIO ── */}
          {step === 2 && (
            <div className="space-y-7 animate-fade-in">
              <div className="text-center">
                <h2 className="text-2xl font-bold text-white tracking-tight">Setup Portfolio</h2>
                <p className="text-sm text-indigo-200/50 mt-1.5 font-medium">
                  Add tickers for <b>{formData.username || 'you'}</b> to monitor
                  {pendingGoogleAuth && <span className="ml-1 text-green-400">(Signed in with Google ✓)</span>}
                </p>
                <div className="mt-4 p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-2xl flex items-start text-left gap-3">
                  <div className="mt-0.5"><Shield className="w-4 h-4 text-indigo-400" /></div>
                  <div>
                    <p className="text-xs text-indigo-300 font-medium leading-relaxed">
                      Enter US stock ticker symbols (e.g., AAPL, TSLA). Our AI will immediately begin analyzing their market footprint.
                    </p>
                  </div>
                </div>
              </div>

              <form onSubmit={addTicker} className="flex gap-3">
                <input
                  type="text"
                  className="flex-1 px-5 py-4 bg-black/20 border border-white/10 rounded-2xl text-white placeholder-white/20 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 font-bold tracking-widest text-lg uppercase transition-all shadow-inner"
                  placeholder="TICKER"
                  value={currentTicker}
                  onChange={e => setCurrentTicker(e.target.value.toUpperCase())}
                />
                <button
                  type="submit"
                  disabled={!currentTicker.trim()}
                  className="bg-white/10 hover:bg-white/20 border border-white/10 px-5 rounded-2xl disabled:opacity-30 transition-all active:scale-[0.96]"
                >
                  <Plus size={24} className="text-white" />
                </button>
              </form>

              <div className="min-h-[140px] bg-black/20 rounded-2xl p-5 flex flex-wrap content-start gap-3 border border-white/5 shadow-inner relative">
                {formData.tickers.length === 0 && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-white/20 text-xs font-bold uppercase tracking-widest">
                    <Activity size={24} className="mb-2 opacity-30" />
                    No Tickers Added
                  </div>
                )}
                {formData.tickers.map(ticker => (
                  <span key={ticker} className="bg-gradient-to-r from-indigo-500/20 to-cyan-500/20 text-cyan-100 border border-cyan-500/30 px-4 py-2 rounded-xl text-sm font-bold tracking-widest flex items-center gap-2 animate-fade-in shadow-lg backdrop-blur-md">
                    {ticker}
                    <button onClick={() => removeTicker(ticker)} className="text-cyan-400/50 hover:text-red-400 transition-colors">
                      <Trash2 size={14} />
                    </button>
                  </span>
                ))}
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => { setStep(1); setPendingGoogleAuth(null) }}
                  className="px-6 py-4 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-semibold rounded-2xl transition-all active:scale-[0.98]"
                >
                  Back
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={loading}
                  className={`flex-1 py-4 px-6 bg-gradient-to-r ${formData.tickers.length === 0 ? 'from-white/10 to-white/5 text-white/50 border border-white/10' : 'from-indigo-500 to-cyan-500 text-white shadow-[0_0_20px_rgba(6,182,212,0.4)] hover:shadow-[0_0_30px_rgba(6,182,212,0.6)]'} hover:opacity-90 font-bold rounded-2xl transition-all flex items-center justify-center gap-3 active:scale-[0.98] disabled:opacity-50`}
                >
                  {loading ? (
                    <Loader className="animate-spin" size={20} />
                  ) : (
                    <>
                      <span>{formData.tickers.length === 0 ? 'Skip & Launch' : 'Launch Dashboard'}</span>
                      <Zap size={18} fill={formData.tickers.length === 0 ? "none" : "currentColor"} className={formData.tickers.length === 0 ? "opacity-50" : ""} />
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  )
}
