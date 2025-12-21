
import React from 'react'

export default function StatCard({ title, value, change, changeType, icon }) {
  const changeColor = {
    positive: 'text-green-400',
    negative: 'text-red-400',
    neutral: 'text-secondary'
  }[changeType] || 'text-secondary'

  return (
    <div className="glass-card rounded-2xl p-5 shadow-xl hover:translate-y-[-2px] transition-all duration-300">
      <div className="flex items-start justify-between mb-2">
        <div>
          <p className="text-secondary text-[10px] uppercase font-black tracking-widest leading-none mb-2">{title}</p>
          <p className="text-3xl font-black text-primary tracking-tighter">{value}</p>
        </div>
        <div className="p-2.5 bg-white/5 rounded-xl border border-white/5 shadow-inner text-primary">
          {icon}
        </div>
      </div>
      <div className="flex items-center gap-1.5 mt-2">
        <div className={`w-1.5 h-1.5 rounded-full ${changeType === 'positive' ? 'bg-green-400' : changeType === 'negative' ? 'bg-red-400' : 'bg-secondary'}`}></div>
        <p className={`text-[10px] font-bold uppercase tracking-tighter ${changeColor}`}>{change}</p>
      </div>
    </div>
  )
}
