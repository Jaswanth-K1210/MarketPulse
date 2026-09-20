import React, { useState } from 'react'
import { HelpCircle, ExternalLink } from 'lucide-react'

export default function AlertCard({ alert, onExplain }) {
  const [expanded, setExpanded] = useState(false)

  const severity = alert.severity || 'medium'
  const icon = alert.icon || '⚠️'
  const impact_percent = alert.impact_percent || alert.impact || 0
  const confidence = alert.confidence || 0.85
  const recommendation = alert.recommendation || 'MONITOR'
  const affected_holdings = alert.affected_holdings || []
  // Robust Chain Display Logic for Elimination Graph
  let chain = ''
  if (typeof alert.chain === 'string') {
    chain = alert.chain
  } else if (alert.chain && typeof alert.chain === 'object') {
    // Check if it has numeric keys or specific level keys
    const parts = []
    if (alert.chain.level1) parts.push(alert.chain.level1)
    if (alert.chain.level2) parts.push(alert.chain.level2)
    if (alert.chain.level3) parts.push(alert.chain.level3)

    // If no level keys, try simple values
    if (parts.length === 0) {
      Object.values(alert.chain).forEach(val => {
        if (val && typeof val === 'string') parts.push(val)
      })
    }
    chain = parts.join(' → ')
  } else if (alert.impactChain) {
    // Support legacy/alternative format
    chain = `${alert.impactChain.level1 || ''} → ${alert.impactChain.level2 || ''} → ${alert.impactChain.level3 || ''}`
  }

  // Clean up any trailing arrows or empty segments
  chain = chain.replace(/ → \s*$/, '').replace(/^ → /, '')

  const explanation = alert.explanation || alert.description || ''
  const sources = alert.sources || []
  const tags = alert.tags || []
  const created_at = alert.created_at || alert.timestamp || new Date().toISOString()

  const getSeverityStyles = (severity) => {
    switch (severity) {
      case 'critical':
      case 'high':
        return {
          border: 'border-l-red-500',
          bg: 'bg-red-500/10',
          hover: 'hover:border-l-red-400',
          badge: 'bg-red-500/20 text-red-300'
        }
      case 'medium':
        return {
          border: 'border-l-yellow-500',
          bg: 'bg-yellow-500/10',
          hover: 'hover:border-l-yellow-400',
          badge: 'bg-yellow-500/20 text-yellow-300'
        }
      default:
        return {
          border: 'border-l-green-500',
          bg: 'bg-green-500/10',
          hover: 'hover:border-l-green-400',
          badge: 'bg-green-500/20 text-green-300'
        }
    }
  }

  const styles = getSeverityStyles(severity)

  return (
    <div className={`group relative overflow-hidden rounded-none border-l-4 p-6 backdrop-blur-sm transition-all hover:shadow-2xl ${styles.border} ${styles.bg} ${styles.hover}`}>
      {/* Alert Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{icon}</span>
          <div>
            <h3 className="text-lg font-semibold text-primary">{alert.title}</h3>
            <p className="text-xs text-secondary">{new Date(created_at).toLocaleString()}</p>
          </div>
        </div>
        <span className={`text-sm font-bold px-3 py-1 rounded-full ${styles.badge}`}>
          {severity.toUpperCase()}
        </span>
      </div>

      {/* Impact Summary */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="rounded-none bg-dark/40 p-3">
          <p className="text-xs text-secondary">Portfolio Impact</p>
          <p className={`text-2xl font-semibold ${impact_percent > 0 ? 'text-green-400' : 'text-red-400'}`}>
            {impact_percent > 0 ? '+' : ''}{impact_percent.toFixed(2)}%
          </p>
        </div>
        <div className="rounded-none bg-dark/40 p-3">
          <p className="text-xs text-secondary">Confidence</p>
          <p className="text-2xl font-semibold text-blue-400">
            {(confidence * 100).toFixed(0)}%
          </p>
        </div>
      </div>

      {/* Affected Holdings */}
      {affected_holdings.length > 0 && (
        <div className="mb-4">
          <p className="text-sm font-semibold text-primary mb-2">💼 Affected Holdings:</p>
          <div className="space-y-2">
            {affected_holdings.map((holding, idx) => (
              <div key={idx} className="flex items-center justify-between rounded bg-black/30 px-3 py-2">
                <span className="text-sm font-medium text-gray-300">{holding.company}</span>
                <span className={`text-sm font-bold ${holding.impact_percent > 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {holding.impact_percent > 0 ? '+' : ''}{holding.impact_percent.toFixed(1)}%
                  {holding.impact_value && ` ($${holding.impact_value > 0 ? '+' : ''}${holding.impact_value.toFixed(2)})`}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Supply Chain */}
      {chain && (
        <div className="mb-4 rounded-none bg-black/20 p-3">
          <p className="text-xs font-semibold text-gray-300 mb-2">⛓️ Supply Chain:</p>
          <p className="text-sm text-gray-400">{chain}</p>
        </div>
      )}

      {/* Explanation */}
      {explanation && (
        <div className="mb-4 rounded-none bg-blue-500/10 border border-blue-500/20 p-3">
          <p className="text-xs font-semibold text-blue-300 mb-1">📊 Analysis:</p>
          <p className="text-sm text-secondary font-medium">{explanation}</p>
        </div>
      )}

      {/* Sources */}
      {sources.length > 0 && (
        <div className="mb-4">
          <p className="text-sm font-semibold text-primary mb-2">📰 Sources:</p>
          <div className="space-y-2">
            {sources.map((source, idx) => {
              try {
                const url = typeof source === 'string' ? source : source.url
                const title = typeof source === 'string' ? new URL(url).hostname.replace('www.', '') : source.title
                return (
                  <a
                    key={idx}
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 rounded bg-black/30 px-3 py-2 transition-all hover:bg-blue-500/20"
                  >
                    <span className="text-blue-400">🔗</span>
                    <span className="flex-1 text-sm text-gray-300 hover:text-blue-400">
                      {title}
                    </span>
                    <span className="text-xs text-gray-600">→</span>
                  </a>
                )
              } catch (e) {
                return (
                  <p key={idx} className="text-xs text-gray-500">• {source}</p>
                )
              }
            })}
          </div>
        </div>
      )}

      {/* Recommendation */}
      <div className="flex items-center gap-2 rounded-none bg-purple-500/10 border border-purple-500/20 p-3 mb-4">
        <span className="text-lg">💡</span>
        <div>
          <p className="text-xs text-gray-400">Recommendation</p>
          <p className="text-sm font-bold text-purple-300">{recommendation}</p>
        </div>
      </div>

      {/* Tags */}
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {tags.map((tag, idx) => (
            <span
              key={idx}
              className="inline-block rounded-full bg-gray-700/50 px-2 py-1 text-xs text-gray-300"
            >
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* Hover Effect */}
      <div className="absolute inset-0 -z-10 bg-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
    </div>
  )
}
