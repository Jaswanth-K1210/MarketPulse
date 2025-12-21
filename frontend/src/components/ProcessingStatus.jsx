import React, { useState, useEffect } from 'react'
import { getNewsFetchStatus } from '../services/api'

export default function ProcessingStatus() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStatus()
    // Poll every 2 seconds when processing
    const interval = setInterval(() => {
      loadStatus()
    }, 2000)

    return () => clearInterval(interval)
  }, [])

  async function loadStatus() {
    try {
      const data = await getNewsFetchStatus()
      setStatus(data)
      setLoading(false)
    } catch (err) {
      console.error('Failed to load processing status:', err)
      setLoading(false)
    }
  }

  if (loading || !status) {
    return null
  }

  const isProcessing = status.status === 'fetching' || status.status === 'processing'
  const progress = status.progress || 0

  // Calculate duration if start_time exists
  let duration = null
  if (status.start_time) {
    const start = new Date(status.start_time)
    const now = new Date()
    duration = Math.floor((now - start) / 1000) // seconds
  }

  return (
    <div className="rounded-lg border border-purple-500/30 bg-gradient-to-r from-purple-500/10 to-blue-500/10 p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className={`h-3 w-3 rounded-full ${isProcessing ? 'bg-purple-500 animate-pulse' : 'bg-green-500'}`}></div>
        <h3 className="font-bold text-primary">
          {isProcessing ? '📡 Processing News...' : '✅ News Updated'}
        </h3>
      </div>

      {isProcessing ? (
        <div className="space-y-3">
          {status.steps && status.steps.map((step, idx) => (
            <div key={idx} className="flex items-center gap-3">
              <div className={`h-2 w-2 rounded-full ${step.status === 'done' ? 'bg-green-500' :
                  step.status === 'processing' ? 'bg-yellow-500 animate-pulse' :
                    'bg-gray-600'
                }`}></div>
              <span className={`text-sm ${step.status === 'done' ? 'text-gray-400' :
                  step.status === 'processing' ? 'text-yellow-300 font-medium' :
                    'text-gray-600'
                }`}>
                {step.status === 'processing' ? '⏳' :
                  step.status === 'done' ? '✅' : '⏸️'}
                {' '}{step.name}
                {step.count > 0 && ` (${step.count} found)`}
              </span>
            </div>
          ))}
          {status.current_step && !status.steps.some(s => s.name === status.current_step) && (
            <div className="flex items-center gap-3">
              <div className="h-2 w-2 rounded-full bg-yellow-500 animate-pulse"></div>
              <span className="text-sm text-yellow-300 font-medium">
                ⏳ {status.current_step}
              </span>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-2 text-sm">
          {status.start_time && (
            <p className="text-gray-400">
              ✅ Last fetch: {new Date(status.start_time).toLocaleString()}
            </p>
          )}
          {status.articles_found > 0 && (
            <p className="text-green-400">
              ✅ Found: {status.articles_found} articles across {status.sources_processed?.length || 0} sources
            </p>
          )}
          {duration !== null && (
            <p className="text-blue-400">
              ✅ Processing time: {duration}s
            </p>
          )}
        </div>
      )}

      <div className="mt-4">
        <div className="h-1 w-full rounded-full bg-gray-700 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-purple-500 to-blue-500 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          ></div>
        </div>
        {isProcessing && (
          <p className="text-xs text-gray-400 mt-2 text-center">
            {progress}% Complete
          </p>
        )}
      </div>
    </div>
  )
}

