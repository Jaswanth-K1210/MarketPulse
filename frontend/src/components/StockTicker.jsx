import React from 'react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

export default function StockTicker({ 
  ticker, 
  price, 
  change, 
  changePercent,
  companyName,
  compact = false 
}) {
  const isPositive = change > 0
  const isNeutral = change === 0
  
  if (compact) {
    // Compact view for inline display
    return (
      <div className="inline-flex items-center gap-2 rounded-lg bg-darkBorder/50 px-3 py-2">
        <span className="text-sm font-bold text-white">{ticker}</span>
        <span className="text-lg font-bold text-white">
          ${price.toFixed(2)}
        </span>
        <span className={`flex items-center gap-1 text-sm font-semibold ${
          isPositive ? 'text-green-400' : isNeutral ? 'text-gray-400' : 'text-red-400'
        }`}>
          {isPositive ? <TrendingUp size={14} /> : isNeutral ? <Minus size={14} /> : <TrendingDown size={14} />}
          {isPositive ? '+' : ''}{changePercent.toFixed(2)}%
        </span>
      </div>
    )
  }
  
  // Full card view
  return (
    <div className="group relative overflow-hidden rounded-lg bg-gradient-to-br from-darkBorder/80 to-darkBorder/40 
                    border border-darkBorder hover:border-blue-500/50 p-4 transition-all duration-300 
                    hover:shadow-lg hover:shadow-blue-500/10">
      {/* Animated gradient overlay on hover */}
      <div className="absolute inset-0 bg-gradient-to-r from-blue-500/0 via-purple-500/0 to-blue-500/0 
                      group-hover:from-blue-500/5 group-hover:via-purple-500/5 group-hover:to-blue-500/5 
                      transition-all duration-500" />
      
      <div className="relative flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              {ticker}
            </p>
            <div className={`h-2 w-2 rounded-full ${
              isPositive ? 'bg-green-500' : isNeutral ? 'bg-gray-500' : 'bg-red-500'
            } animate-pulse`} />
          </div>
          <p className="text-sm text-gray-500 mt-0.5 truncate max-w-[150px]">
            {companyName || ticker}
          </p>
        </div>
        
        <div className="text-right">
          <p className="text-2xl font-bold text-white transition-all group-hover:scale-110">
            ${price.toFixed(2)}
          </p>
          
          <div className={`flex items-center justify-end gap-1 mt-1 rounded-full px-2 py-1 ${
            isPositive 
              ? 'bg-green-500/20 text-green-400' 
              : isNeutral
              ? 'bg-gray-500/20 text-gray-400'
              : 'bg-red-500/20 text-red-400'
          }`}>
            {isPositive ? (
              <TrendingUp size={14} />
            ) : isNeutral ? (
              <Minus size={14} />
            ) : (
              <TrendingDown size={14} />
            )}
            <span className="text-xs font-semibold">
              {isPositive ? '+' : ''}{change.toFixed(2)}
            </span>
            <span className="text-xs font-bold">
              ({isPositive ? '+' : ''}{changePercent.toFixed(2)}%)
            </span>
          </div>
        </div>
      </div>
      
      {/* Animated bottom border */}
      <div className={`absolute bottom-0 left-0 h-0.5 w-0 transition-all duration-500 ease-out 
                       group-hover:w-full ${
        isPositive ? 'bg-gradient-to-r from-green-500 to-emerald-400' : 
        isNeutral ? 'bg-gradient-to-r from-gray-500 to-gray-400' :
        'bg-gradient-to-r from-red-500 to-rose-400'
      }`} />
    </div>
  )
}
