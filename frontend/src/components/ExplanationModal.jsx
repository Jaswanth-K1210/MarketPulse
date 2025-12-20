import React, { useState, useEffect } from 'react'
import { X, Lightbulb, Zap } from 'lucide-react'

export default function ExplanationModal({ alert, onClose }) {
  const [isLoading, setIsLoading] = useState(true)
  const [explanation, setExplanation] = useState('')

  useEffect(() => {
    // Simulate API call to get AI explanation
    const timer = setTimeout(() => {
      setExplanation(alert.explanation || "Unable to generate explanation at this time.")
      setIsLoading(false)
    }, 1500)
    return () => clearTimeout(timer)
  }, [alert])

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-darkBg border border-darkBorder rounded-lg w-full max-w-2xl max-h-[80vh] overflow-auto">
        {/* Header */}
        <div className="sticky top-0 bg-darkBg border-b border-darkBorder px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Lightbulb size={22} className="text-yellow-400" />
            <h2 className="text-xl font-bold">AI Explanation</h2>
          </div>
          <button onClick={onClose} className="hover:bg-darkBorder p-2 rounded-lg transition-colors">
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Alert Summary */}
          <div className="bg-darkBorder border border-darkBorder rounded-lg p-4">
            <p className="text-xs text-gray-400 mb-2">ALERT SUMMARY</p>
            <h3 className="font-bold text-lg mb-2">{alert.title}</h3>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-xs text-gray-400">Company</p>
                <p className="font-bold">{alert.company} ({alert.ticker})</p>
              </div>
              <div>
                <p className="text-xs text-gray-400">Impact</p>
                <p className={`font-bold text-lg ${alert.impact > 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {alert.impact > 0 ? '+' : ''}{alert.impact}%
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-400">Confidence</p>
                <p className="font-bold">{(alert.confidence * 100).toFixed(0)}%</p>
              </div>
            </div>
          </div>

          {/* Explanation */}
          <div className="space-y-3">
            <h3 className="font-bold text-lg flex items-center gap-2">
              <Zap size={20} className="text-blue-400" />
              Why This Matters
            </h3>
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                <span className="ml-3 text-gray-400">Generating AI explanation...</span>
              </div>
            ) : (
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 text-gray-200 leading-relaxed">
                <p>{explanation}</p>
              </div>
            )}
          </div>

          {/* Impact Chain */}
          <div className="space-y-3">
            <h3 className="font-bold text-lg">Impact Chain Analysis</h3>
            <div className="space-y-2 bg-darkBorder rounded-lg p-4">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-blue-500/20 border border-blue-500 flex items-center justify-center text-blue-400 font-bold text-sm flex-shrink-0">
                  1
                </div>
                <div>
                  <p className="text-xs text-gray-400">Initial Event</p>
                  <p className="text-sm">{alert.impactChain.level1}</p>
                </div>
              </div>
              <div className="flex justify-center text-blue-400">↓</div>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-blue-500/20 border border-blue-500 flex items-center justify-center text-blue-400 font-bold text-sm flex-shrink-0">
                  2
                </div>
                <div>
                  <p className="text-xs text-gray-400">Direct Impact</p>
                  <p className="text-sm">{alert.impactChain.level2}</p>
                </div>
              </div>
              <div className="flex justify-center text-blue-400">↓</div>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-blue-500/20 border border-blue-500 flex items-center justify-center text-blue-400 font-bold text-sm flex-shrink-0">
                  3
                </div>
                <div>
                  <p className="text-xs text-gray-400">Portfolio Impact</p>
                  <p className="text-sm">{alert.impactChain.level3}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Key Insights */}
          <div className="space-y-3">
            <h3 className="font-bold text-lg">Key Insights</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3">
                <p className="text-xs text-gray-400 mb-1">Recommendation</p>
                <p className="font-bold text-green-400">{alert.recommendation}</p>
              </div>
              <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-3">
                <p className="text-xs text-gray-400 mb-1">Confidence Level</p>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-darkBorder rounded-full h-2">
                    <div
                      className="bg-purple-500 h-2 rounded-full"
                      style={{ width: `${alert.confidence * 100}%` }}
                    ></div>
                  </div>
                  <span className="font-bold">{(alert.confidence * 100).toFixed(0)}%</span>
                </div>
              </div>
            </div>
          </div>

          {/* Action Button */}
          <div className="flex gap-3 pt-4">
            <button
              onClick={onClose}
              className="flex-1 bg-darkBorder hover:bg-darkBorder/80 border border-darkBorder py-2 rounded-lg transition-colors font-bold"
            >
              Close
            </button>
            <button className="flex-1 bg-blue-500 hover:bg-blue-600 text-white py-2 rounded-lg transition-colors font-bold">
              Act on This Alert
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
