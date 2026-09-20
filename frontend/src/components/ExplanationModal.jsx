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

  // Normalize Chain Data
  const chainObj = alert.impactChain || alert.chain || {}
  const level1 = chainObj.level1 || "Event Trigger"
  const level2 = chainObj.level2 || "Intermediary Impact"
  const level3 = chainObj.level3 || "Portfolio Result"


  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fade-in">
      <div className="glass-card border border-white/5 rounded-[2rem] w-full max-w-2xl max-h-[90vh] overflow-hidden shadow-2xl flex flex-col">
        {/* Header */}
        <div className="bg-dark/40 backdrop-blur border-b border-white/5 px-8 py-6 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-yellow-500/10 rounded-none">
              <Lightbulb size={24} className="text-yellow-400" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-primary">Intelligence Brief</h2>
              <div className="flex items-center gap-1.5">
                <span className="w-1 h-1 bg-yellow-500 rounded-full animate-pulse"></span>
                <p className="text-[10px] text-gray-500 font-bold leading-none">AI Insight Protocol</p>
              </div>
            </div>
          </div>
          <button onClick={onClose} className="bg-white/5 hover:bg-white/10 p-2.5 rounded-none transition-all active:scale-95">
            <X size={20} className="text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-8 space-y-10 overflow-auto">
          {/* Alert Summary */}
          <div className="bg-white/5 border border-white/10 rounded-none p-6 relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 blur-3xl rounded-full -mr-16 -mt-16"></div>
            <p className="text-[10px] font-semibold text-blue-500 tracking-[0.2em] mb-3 ml-1">Alert Summary</p>
            <h3 className="text-2xl font-semibold text-primary mb-6 leading-tight">{alert.title}</h3>
            <div className="grid grid-cols-3 gap-6">
              <div className="bg-dark/40 p-3 rounded-none border border-white/5">
                <p className="text-[10px] text-gray-500 font-bold mb-1">Company</p>
                <p className="text-sm font-semibold text-primary truncate">{alert.company} <span className="text-blue-500">[{alert.ticker}]</span></p>
              </div>
              <div className="bg-dark/40 p-3 rounded-none border border-white/5 text-center">
                <p className="text-[10px] text-gray-500 font-bold mb-1">Estimated Impact</p>
                <p className={`text-xl font-semibold ${alert.impact > 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {alert.impact > 0 ? '+' : ''}{alert.impact}%
                </p>
              </div>
              <div className="bg-dark/40 p-3 rounded-none border border-white/5 text-right">
                <p className="text-[10px] text-gray-500 font-bold mb-1">AI Confidence</p>
                <p className="text-xl font-semibold text-primary font-mono">{(alert.confidence * 100).toFixed(0)}%</p>
              </div>
            </div>
          </div>

          {/* Explanation */}
          <div className="space-y-4">
            <h3 className="text-xs font-semibold text-purple-400 flex items-center gap-3">
              <div className="w-1.5 h-1.5 bg-purple-500 rounded-full"></div>
              Strategic assessment
            </h3>
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-12 bg-dark/20 rounded-none border border-dashed border-white/5">
                <div className="relative">
                  <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <Zap size={16} className="text-blue-500 animate-pulse" />
                  </div>
                </div>
                <span className="mt-6 text-[10px] font-semibold text-gray-500 animate-pulse">Running Neural Synthesis...</span>
              </div>
            ) : (
              <div className="bg-blue-500/10 border border-white/5 rounded-none p-6 text-gray-300 leading-relaxed shadow-lg">
                <p className="text-sm lg:text-base font-medium">{explanation}</p>
              </div>
            )}
          </div>

          {/* Impact Chain */}
          <div className="space-y-6">
            <h3 className="text-xs font-semibold text-blue-400 flex items-center gap-3">
              <div className="w-1.5 h-1.5 bg-blue-500 rounded-full"></div>
              Impact Propogation Chain
            </h3>
            <div className="space-y-2 px-2">
              <div className="flex items-start gap-6 relative group">
                <div className="w-6 h-6 rounded-none bg-blue-500/20 border border-blue-500/40 flex items-center justify-center text-blue-400 font-bold text-xs shrink-0 z-10">
                  1
                </div>
                <div className="absolute top-6 left-3 w-[1px] h-full bg-blue-500/40"></div>
                <div className="pb-8">
                  <p className="text-[10px] text-gray-500 font-semibold mb-1">Initial Trigger</p>
                  <p className="text-sm font-bold text-gray-300">{level1}</p>
                </div>
              </div>

              <div className="flex items-start gap-6 relative group">
                <div className="w-6 h-6 rounded-none bg-blue-500/20 border border-blue-500/40 flex items-center justify-center text-blue-400 font-bold text-xs shrink-0 z-10">
                  2
                </div>
                <div className="absolute top-6 left-3 w-[1px] h-full bg-blue-500/40"></div>
                <div className="pb-8">
                  <p className="text-[10px] text-gray-500 font-semibold mb-1">Direct Consequence</p>
                  <p className="text-sm font-bold text-gray-300">{level2}</p>
                </div>
              </div>

              <div className="flex items-start gap-6 relative group">
                <div className="w-6 h-6 rounded-none bg-green-500/20 border border-green-500/40 flex items-center justify-center text-green-400 font-bold text-xs shrink-0 z-10 shadow-[0_0_10px_rgba(74,222,128,0.3)]">
                  3
                </div>
                <div className="">
                  <p className="text-[10px] text-green-500 font-semibold mb-1">Portfolio Result</p>
                  <p className="text-sm font-semibold text-primary">{level3}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Key Insights */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-green-500/5 border border-green-500/20 rounded-none p-5 group hover:bg-green-500/10 transition-colors">
              <p className="text-[10px] text-green-500 font-semibold mb-2">Protocol Action</p>
              <p className="text-sm font-semibold text-primary">{alert.recommendation}</p>
            </div>
            <div className="bg-blue-500/5 border border-white/5 rounded-none p-5">
              <p className="text-[10px] text-gray-500 font-semibold mb-2">Confidence Metric</p>
              <div className="flex items-center gap-4">
                <div className="flex-1 bg-white/5 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-blue-600 h-full transition-all duration-1000 ease-out"
                    style={{ width: `${alert.confidence * 100}%` }}
                  ></div>
                </div>
                <span className="text-sm font-mono font-semibold text-primary">{(alert.confidence * 100).toFixed(0)}%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-8 bg-dark/40 border-t border-white/5 flex gap-4 shrink-0">
          <button
            onClick={onClose}
            className="flex-1 px-6 py-4 rounded-none text-secondary hover:text-primary hover:bg-white/5 transition-all text-xs font-semibold border border-transparent hover:border-white/5"
          >
            Dismiss
          </button>
          <button className="flex-[2] bg-blue-600 text-white py-4 rounded-none transition-all shadow-xl shadow-blue-600/20 active:scale-95 text-xs font-semibold">
            Acknowledge & Sync
          </button>
        </div>
      </div>
    </div>
  )
}
