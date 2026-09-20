import React from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function AlertTrendChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
        <XAxis dataKey="day" stroke="#6B7280" style={{ fontSize: '12px' }} />
        <YAxis stroke="#6B7280" style={{ fontSize: '12px' }} />
        <Tooltip
          contentStyle={{ backgroundColor: '#101010', border: '1px solid #2a2a2a', borderRadius: '0' }}
          labelStyle={{ color: '#E5E7EB' }}
        />
        <Line
          type="monotone"
          dataKey="alerts"
          stroke="#4ade80"
          strokeWidth={2}
          dot={{ fill: '#4ade80', r: 4 }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
