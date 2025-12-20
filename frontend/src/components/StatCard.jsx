import React from 'react'

export default function StatCard({ title, value, change, changeType, icon }) {
  const changeColor = {
    positive: 'text-green-400',
    negative: 'text-red-400',
    neutral: 'text-gray-400'
  }[changeType]

  return (
    <div className="bg-darkBg border border-darkBorder rounded-lg p-4 hover:border-blue-500/30 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="text-gray-400 text-sm">{title}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
        </div>
        <div className="p-2 bg-darkBorder rounded-lg">
          {icon}
        </div>
      </div>
      <p className={`text-xs ${changeColor}`}>{change}</p>
    </div>
  )
}
