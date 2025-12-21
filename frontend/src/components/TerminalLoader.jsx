import React, { useState, useEffect, useRef } from 'react';
import { Terminal, Check, Activity, Shield, Globe, Zap, Cpu } from 'lucide-react';

const LOGS = [
    { agent: 'SYSTEM', message: 'Initializing MarketPulse-X Core...', type: 'info', icon: Terminal },
    { agent: 'AUTH', message: 'Verifying user credentials...', type: 'success', icon: Shield },
    { agent: 'AGENT-1', message: 'Connecting to News Ingestion Layer...', type: 'info', icon: Globe },
    { agent: 'AGENT-1', message: 'Stream established: Reuters, Bloomberg, WSJ.', type: 'success', icon: Check },
    { agent: 'AGENT-2', message: 'Booting Classification Matrix (v3.0)...', type: 'info', icon: Cpu },
    { agent: 'AGENT-3', message: 'Scanning for Supply Chain dependencies...', type: 'warning', icon: Activity },
    { agent: 'AGENT-4', message: 'Calculating portfolio impact vectors...', type: 'info', icon: Zap },
    { agent: 'SYSTEM', message: 'Constructing Knowledge Graph...', type: 'info', icon: Activity },
    { agent: 'SYSTEM', message: 'Optimization complete. Launching Dashboard.', type: 'success', icon: Check }
];

export default function TerminalLoader({ onComplete }) {
    const [lines, setLines] = useState([]);
    const [progress, setProgress] = useState(0);
    const scrollRef = useRef(null);

    useEffect(() => {
        let currentIndex = 0;
        const totalDuration = 3500; // 3.5 seconds total
        const intervalTime = totalDuration / LOGS.length;

        const timer = setInterval(() => {
            if (currentIndex < LOGS.length) {
                setLines(prev => [...prev, LOGS[currentIndex]]);
                setProgress(((currentIndex + 1) / LOGS.length) * 100);
                currentIndex++;
            } else {
                clearInterval(timer);
                // Ensure onComplete is called only once
                setTimeout(() => {
                    onComplete();
                }, 800);
            }
        }, intervalTime);

        return () => clearInterval(timer);
    }, []); // Removed onComplete from dependency array to prevent re-runs/cancellations

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [lines]);

    return (
        <div className="fixed inset-0 bg-darker z-50 flex items-center justify-center p-4">
            {/* Background Effects */}
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 via-purple-500 to-blue-500 animate-pulse"></div>
            <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-5 pointer-events-none"></div>

            <div className="w-full max-w-2xl bg-black/90 rounded-xl border border-white/10 shadow-2xl overflow-hidden glass-terminal backdrop-blur-xl">
                {/* Header */}
                <div className="bg-white/5 px-4 py-3 flex items-center justify-between border-b border-white/5">
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
                        <div className="w-3 h-3 rounded-full bg-yellow-500/80"></div>
                        <div className="w-3 h-3 rounded-full bg-green-500/80"></div>
                    </div>
                    <div className="text-secondary text-xs font-mono flex items-center gap-2">
                        <Terminal size={12} />
                        MARKETPULSE_KERNEL_V3.0
                    </div>
                </div>

                {/* Content */}
                <div className="p-6 h-[400px] flex flex-col font-mono text-sm relative">

                    {/* Log Stream */}
                    <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-3 custom-scrollbar pr-2">
                        {lines.map((log, idx) => {
                            const Icon = log.icon;
                            return (
                                <div key={idx} className="flex items-start gap-3 animate-fade-in">
                                    <span className="text-white/20 text-xs mt-1">
                                        {new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                                    </span>
                                    <div className={`p-1 rounded ${log.type === 'success' ? 'bg-green-500/10 text-green-400' :
                                        log.type === 'warning' ? 'bg-yellow-500/10 text-yellow-400' :
                                            'bg-blue-500/10 text-blue-400'
                                        }`}>
                                        <Icon size={14} />
                                    </div>
                                    <div className="flex-1">
                                        <span className={`text-xs font-bold mr-2 ${log.agent === 'SYSTEM' ? 'text-purple-400' : 'text-cyan-400'
                                            }`}>
                                            {log.agent} &gt;
                                        </span>
                                        <span className="text-gray-300">{log.message}</span>
                                    </div>
                                </div>
                            );
                        })}
                        {lines.length < LOGS.length && (
                            <div className="animate-pulse text-blue-500 font-bold">_</div>
                        )}
                    </div>

                    {/* Progress Bar */}
                    <div className="mt-6 pt-4 border-t border-white/10">
                        <div className="flex justify-between text-xs text-secondary mb-2 uppercase tracking-widest">
                            <span>System Initialization</span>
                            <span>{Math.round(progress)}%</span>
                        </div>
                        <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-300 ease-out"
                                style={{ width: `${progress}%` }}
                            ></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
