import React, { useState } from 'react'
import { X, CheckCircle, ArrowRight } from 'lucide-react'
import { mockTriggerArticle, mockCascadeResult } from '../utils/mockData'

export default function TriggerModal({ onClose, onProcess, triggerEvent }) {
  const [step, setStep] = useState('article') // article -> validation -> extraction -> cascade -> result
  const [isProcessing, setIsProcessing] = useState(false)

  // Use trigger event data if provided, otherwise use mock data
  const articleData = triggerEvent?.article || mockTriggerArticle
  const cascadeData = triggerEvent?.cascade || mockCascadeResult.cascade
  const affectedHoldingsData = triggerEvent?.affectedHoldings || mockCascadeResult.affectedHoldings
  const explanationData = triggerEvent?.explanation || mockCascadeResult.explanation
  const recommendationData = triggerEvent?.recommendation || mockCascadeResult.recommendation

  const handleStartProcessing = async () => {
    setIsProcessing(true)
    setStep('validation')

    // Simulate processing steps with delays
    await new Promise(r => setTimeout(r, 800))
    setStep('extraction')

    await new Promise(r => setTimeout(r, 800))
    setStep('cascade')

    await new Promise(r => setTimeout(r, 800))
    setStep('result')

    setIsProcessing(false)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-darkBg border border-darkBorder rounded-lg w-full max-w-2xl max-h-[90vh] overflow-auto">
        {/* Header */}
        <div className="sticky top-0 bg-darkBg border-b border-darkBorder px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-bold">Pipeline Workflow</h2>
          <button onClick={onClose} className="hover:bg-darkBorder p-2 rounded-lg transition-colors">
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Step 1: Article */}
          {step === 'article' && (
            <div className="space-y-4 animate-fade-in">
              <h3 className="font-bold text-lg">Step 1: News Article</h3>
              <div className="bg-darkBorder border border-darkBorder rounded-lg p-4 space-y-3">
                <div>
                  <p className="text-xs text-gray-400 mb-1">Source</p>
                  <p className="font-bold">{articleData.source}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 mb-1">Title</p>
                  <p className="text-sm">{articleData.title}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 mb-1">Content Preview</p>
                  <p className="text-sm text-gray-300">{articleData.content.substring(0, 200)}...</p>
                </div>
              </div>
              <button
                onClick={handleStartProcessing}
                className="w-full bg-blue-500 hover:bg-blue-600 text-white font-bold py-3 rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                Process Through Pipeline
                <ArrowRight size={18} />
              </button>
            </div>
          )}

          {/* Step 2: Validation */}
          {step === 'validation' && (
            <div className="space-y-4 animate-fade-in">
              <h3 className="font-bold text-lg flex items-center gap-2">
                <span className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center text-white">1</span>
                Event Validator
              </h3>
              <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4 space-y-2">
                <div className="flex items-center gap-2">
                  <CheckCircle size={18} className="text-green-400" />
                  <span>✓ Schema validation passed</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle size={18} className="text-green-400" />
                  <span>✓ Content quality acceptable</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle size={18} className="text-green-400" />
                  <span>✓ Companies mentioned: {articleData.companies.join(', ')}</span>
                </div>
              </div>
              <p className="text-sm text-gray-300">Validating article structure and relevance...</p>
            </div>
          )}

          {/* Step 3: Extraction */}
          {step === 'extraction' && (
            <div className="space-y-4 animate-fade-in">
              <h3 className="font-bold text-lg flex items-center gap-2">
                <span className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white">2</span>
                Relation Extractor
              </h3>
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 space-y-3">
                {triggerEvent?.relationships.map((rel, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <p className="font-bold">{rel.from}</p>
                    <ArrowRight size={16} className="text-blue-400" />
                    <p className="font-bold">{rel.to}</p>
                    <span className="ml-auto text-xs bg-blue-500 text-white px-2 py-1 rounded">
                      {(rel.confidence * 100).toFixed(0)}% confidence
                    </span>
                  </div>
                )) || mockCascadeResult.relationships.map((rel, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <p className="font-bold">{rel.from}</p>
                    <ArrowRight size={16} className="text-blue-400" />
                    <p className="font-bold">{rel.to}</p>
                    <span className="ml-auto text-xs bg-blue-500 text-white px-2 py-1 rounded">
                      {(rel.confidence * 100).toFixed(0)}% confidence
                    </span>
                  </div>
                ))}
              </div>
              <p className="text-sm text-gray-300">Extracting company relationships using AI...</p>
            </div>
          )}

          {/* Step 4: Cascade */}
          {step === 'cascade' && (
            <div className="space-y-4 animate-fade-in">
              <h3 className="font-bold text-lg flex items-center gap-2">
                <span className="w-8 h-8 bg-purple-500 rounded-full flex items-center justify-center text-white">3</span>
                Cascade Inferencer
              </h3>
              <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4 space-y-3">
                <div className="space-y-2">
                  <p className="text-xs text-gray-400">Level 1 (Event)</p>
                  <p className="text-sm font-bold">{cascadeData.level1}</p>
                </div>
                <div className="text-center text-purple-400">↓</div>
                <div className="space-y-2">
                  <p className="text-xs text-gray-400">Level 2 (Direct Impact)</p>
                  <p className="text-sm font-bold">{cascadeData.level2}</p>
                </div>
                <div className="text-center text-purple-400">↓</div>
                <div className="space-y-2">
                  <p className="text-xs text-gray-400">Level 3 (Portfolio Impact)</p>
                  <p className="text-sm font-bold text-red-400">{cascadeData.level3}</p>
                </div>
              </div>
              <p className="text-sm text-gray-300">Inferring cascade effects through supply chain...</p>
            </div>
          )}

          {/* Step 5: Result */}
          {(step === 'result' || (step !== 'article' && !isProcessing)) && (
            <div className="space-y-4 animate-fade-in">
              <h3 className="font-bold text-lg flex items-center gap-2">
                <span className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center text-white">✓</span>
                Pipeline Complete
              </h3>

              {/* Affected Holdings */}
              <div className="space-y-2">
                <p className="text-sm text-gray-400">Affected Portfolio Holdings</p>
                {affectedHoldingsData.map((h, i) => (
                  <div key={i} className="bg-darkBorder border border-red-500/30 rounded-lg p-3 flex items-center justify-between">
                    <div>
                      <p className="font-bold">{h.company} ({h.ticker})</p>
                      <p className="text-xs text-gray-400">{(h.confidence * 100).toFixed(0)}% confidence</p>
                    </div>
                    <p className="text-lg font-bold text-red-400">{h.impact > 0 ? '+' : ''}{h.impact}%</p>
                  </div>
                ))}
              </div>

              {/* Explanation */}
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
                <p className="text-sm text-gray-200">{explanationData}</p>
              </div>

              {/* Recommendation */}
              <div className="bg-darkBorder border border-yellow-500/30 rounded-lg p-4 flex items-center justify-between">
                <div>
                  <p className="text-xs text-gray-400">Recommendation</p>
                  <p className="font-bold text-lg">{recommendationData}</p>
                </div>
                <button
                  onClick={() => {
                    const resultData = {
                      article: articleData,
                      cascade: cascadeData,
                      affectedHoldings: affectedHoldingsData,
                      explanation: explanationData,
                      recommendation: recommendationData,
                      companies: articleData.companies,
                      relationships: triggerEvent?.relationships || mockCascadeResult.relationships
                    }
                    onProcess(resultData)
                    onClose()
                  }}
                  className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg transition-colors font-bold"
                >
                  Create Alert
                </button>
              </div>
            </div>
          )}

          {/* Processing Indicator */}
          {isProcessing && step !== 'result' && (
            <div className="flex items-center justify-center py-4">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
              <span className="ml-3 text-gray-400">Processing...</span>
            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        .animate-fade-in {
          animation: fade-in 0.3s ease-in;
        }
      `}</style>
    </div>
  )
}
