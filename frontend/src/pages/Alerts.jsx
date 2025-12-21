
import React, { useState, useEffect } from 'react'
import { AlertCircle, AlertTriangle, Info, CheckCircle, ExternalLink } from 'lucide-react'

export default function Alerts() {
    const [alerts, setAlerts] = useState([])
    const [loading, setLoading] = useState(true)

    const fetchAlerts = async () => {
        try {
            setLoading(true)
            const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/alerts`)
            const data = await res.json()
            if (data.status === 'success') {
                // Normalize alerts
                const normalized = (data.data || []).map(alert => ({
                    ...alert,
                    severity: alert.severity || 'Medium',
                    timestamp: alert.created_at || new Date().toISOString()
                }))
                setAlerts(normalized)
            }
        } catch (err) {
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchAlerts()
    }, [])

    const getSeverityColor = (severity) => {
        switch (severity.toLowerCase()) {
            case 'high': return 'text-red-400 bg-red-400/10 border-red-400/20'
            case 'medium': return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20'
            case 'low': return 'text-blue-400 bg-blue-400/10 border-blue-400/20'
            default: return 'text-gray-400 bg-gray-400/10 border-gray-400/20'
        }
    }

    const getSeverityIcon = (severity) => {
        switch (severity.toLowerCase()) {
            case 'high': return <AlertCircle size={20} />
            case 'medium': return <AlertTriangle size={20} />
            case 'low': return <Info size={20} />
            default: return <CheckCircle size={20} />
        }
    }

    return (
        <div className="p-8">
            <div className="mb-8">
                <h2 className="text-2xl font-bold">Risk Alerts</h2>
                <p className="text-gray-400">Real-time portfolio impact warnings</p>
            </div>

            {loading && alerts.length === 0 ? (
                <div className="text-center py-20 text-gray-500">Loading alerts...</div>
            ) : alerts.length === 0 ? (
                <div className="text-center py-20 bg-darkBg border border-darkBorder rounded-xl border-dashed">
                    <p className="text-gray-400">No active alerts detected.</p>
                    <p className="text-sm text-gray-500 mt-2">Your portfolio looks safe currently.</p>
                </div>
            ) : (
                <div className="space-y-4">
                    {alerts.map((alert, idx) => (
                        <div key={alert.id || idx} className={`p-6 rounded-xl border ${getSeverityColor(alert.severity)}`}>
                            <div className="flex items-start gap-4">
                                <div className="mt-1">
                                    {getSeverityIcon(alert.severity)}
                                </div>
                                <div className="flex-1">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="font-bold uppercase text-sm tracking-wider">{alert.severity} IMPLICATION</span>
                                        <span className="text-xs opacity-70">{new Date(alert.timestamp).toLocaleString()}</span>
                                    </div>
                                    <h3 className="text-xl font-bold text-white mb-2">{alert.title}</h3>
                                    <p className="text-gray-300 leading-relaxed mb-4">{alert.reasoning || alert.description}</p>

                                    {alert.affected_holdings && alert.affected_holdings.length > 0 && (
                                        <div className="flex flex-wrap gap-2 mb-4">
                                            {alert.affected_holdings.map((h, i) => (
                                                <span key={i} className="px-2 py-1 bg-dark/50 rounded text-xs font-mono border border-white/10">
                                                    {h.ticker || h.company}
                                                </span>
                                            ))}
                                        </div>
                                    )}

                                    <div className="flex items-center gap-4">
                                        {alert.source_url && (
                                            <a
                                                href={alert.source_url}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="text-sm font-medium underline opacity-80 hover:opacity-100 flex items-center gap-1"
                                            >
                                                Read Source <ExternalLink size={14} />
                                            </a>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
