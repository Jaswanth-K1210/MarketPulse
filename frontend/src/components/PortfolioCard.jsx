import React, { useEffect, useState } from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'

export default function PortfolioCard({ holding }) {
  // Use current_price or fall back to currentPrice for backwards compatibility
  const currentPrice = holding.current_price || holding.currentPrice || 0
  const purchasePrice = holding.purchase_price || holding.purchasePrice || 0
  const quantity = holding.quantity || 0

  const totalValue = holding.current_value || (quantity * currentPrice)
  const gainLoss = holding.gain_loss || ((currentPrice - purchasePrice) * quantity)
  const gainLossPercent = holding.gain_loss_percent || (((currentPrice - purchasePrice) / purchasePrice) * 100)

  // Day change (optional, if available from backend)
  const dayChange = holding.day_change_percent || 0
  const isDayPositive = dayChange >= 0
  const isGainPositive = gainLoss >= 0

  // Animated price change indicator
  const [priceFlash, setPriceFlash] = useState(false)

  useEffect(() => {
    if (dayChange !== 0) {
      setPriceFlash(true)
      const timer = setTimeout(() => setPriceFlash(false), 1000)
      return () => clearTimeout(timer)
    }
  }, [currentPrice])

  return (
    <div className="group relative overflow-hidden bg-white/5 border border-white/5 hover:border-blue-500/50 rounded-2xl p-5 transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/10">
      {/* Gradient background on hover */}
      <div className="absolute inset-0 bg-gradient-to-r from-blue-500/0 to-purple-500/0 group-hover:from-blue-500/5 group-hover:to-purple-500/5 transition-all duration-300" />

      {/* Price flash animation */}
      {priceFlash && (
        <div className={`absolute inset-0 ${isDayPositive ? 'bg-green-500/10' : 'bg-red-500/10'} animate-pulse`} />
      )}

      <div className="relative flex items-center justify-between">
        <div className="flex items-center gap-3 flex-1">
          {/* Ticker Icon */}
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white font-bold shadow-lg shadow-blue-500/30 group-hover:scale-110 transition-transform duration-300">
            {holding.ticker?.charAt(0) || '?'}
          </div>

          {/* Company Info */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <p className="font-black text-primary uppercase tracking-widest">{holding.ticker}</p>
              {dayChange !== 0 && (
                <span className={`text-xs px-1.5 py-0.5 rounded animate-pulse ${isDayPositive ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                  }`}>
                  {isDayPositive ? '+' : ''}{dayChange.toFixed(2)}%
                </span>
              )}
            </div>
            <p className="text-xs text-secondary font-bold truncate uppercase tracking-tighter opacity-70">{holding.company}</p>
            <p className="text-[10px] text-secondary mt-1 font-bold uppercase tracking-widest">
              {quantity} shares @ <span className="font-black text-primary">${currentPrice.toFixed(2)}</span>
            </p>
          </div>
        </div>

        {/* Value & Performance */}
        <div className="text-right">
          <p className="text-lg font-black text-primary transition-all group-hover:scale-105">
            ${totalValue.toLocaleString('en-US', { maximumFractionDigits: 0 })}
          </p>

          {/* Gain/Loss */}
          <div className="flex items-center justify-end gap-1 mt-1">
            {isGainPositive ? (
              <TrendingUp size={14} className="text-green-400 animate-bounce" />
            ) : (
              <TrendingDown size={14} className="text-red-400 animate-bounce" />
            )}
            <p className={`text-sm font-bold ${isGainPositive ? 'text-green-400' : 'text-red-400'}`}>
              {isGainPositive ? '+' : ''}${Math.abs(gainLoss).toLocaleString('en-US', { maximumFractionDigits: 0 })}
            </p>
          </div>

          <p className={`text-xs ${isGainPositive ? 'text-green-400/70' : 'text-red-400/70'}`}>
            {isGainPositive ? '+' : ''}{gainLossPercent.toFixed(1)}%
          </p>
        </div>
      </div>

      {/* Bottom progress bar */}
      <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gray-700/30">
        <div
          className={`h-full transition-all duration-500 ${isGainPositive ? 'bg-gradient-to-r from-green-500 to-emerald-400' : 'bg-gradient-to-r from-red-500 to-rose-400'
            }`}
          style={{ width: `${Math.min(Math.abs(gainLossPercent) * 2, 100)}%` }}
        />
      </div>
    </div>
  )
}
