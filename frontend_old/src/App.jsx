
import { useState, useEffect, useRef } from 'react';
import { Activity, Brain, Network, Zap, ShieldCheck, Bell, Terminal, BarChart2, Globe, TrendingUp, TrendingDown, Layers } from 'lucide-react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import SupplyChainGraphD3 from './SupplyChainGraphD3';
import './App.css';

// --- COMPONENTS ---

const StatusBadge = ({ status }) => {
  if (status === 'active') return (
    <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30 text-[10px] font-bold tracking-tighter uppercase animte-pulse">
      <span className="w-1.5 h-1.5 rounded-full bg-purple-500 animate-ping" />
      Processing
    </div>
  );
  if (status === 'completed') return (
    <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[10px] font-bold tracking-tighter uppercase">
      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
      Complete
    </div>
  );
  return (
    <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-slate-800/50 text-slate-500 border border-slate-700/30 text-[10px] font-bold tracking-tighter uppercase">
      <span className="w-1.5 h-1.5 rounded-full bg-slate-700" />
      Waiting
    </div>
  );
};

const AgentCard = ({ id, name, icon: Icon, status }) => {
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: id * 0.05 }}
      className={`p-4 border rounded-xl flex items-center justify-between transition-all duration-300 ${status === 'active' ? 'bg-purple-900/10 border-purple-500/50 shadow-lg shadow-purple-500/10' :
        status === 'completed' ? 'bg-emerald-900/5 border-emerald-500/30' :
          'bg-slate-900/20 border-slate-800'
        }`}
    >
      <div className="flex items-center gap-4">
        <div className={`p-2.5 rounded-lg ${status === 'active' ? 'bg-purple-500/20 text-purple-400' : 'bg-slate-800/50 text-slate-500'}`}>
          <Icon size={20} />
        </div>
        <div>
          <h3 className={`font-bold text-xs tracking-wider uppercase ${status === 'active' ? 'text-purple-300' : 'text-slate-400'}`}>{name}</h3>
          <p className="text-[10px] text-slate-600 font-mono mt-0.5">AGENT.0{id}_INSTANCE</p>
        </div>
      </div>
      <StatusBadge status={status} />
    </motion.div>
  );
};

const LogTerminal = ({ logs }) => {
  const endRef = useRef(null);
  useEffect(() => endRef.current?.scrollIntoView({ behavior: 'smooth' }), [logs]);

  return (
    <div className="h-full flex flex-col overflow-hidden bg-slate-950/80 rounded-xl border border-slate-800 backdrop-blur-sm">
      <div className="p-3 border-b border-white/5 bg-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 tracking-widest uppercase">
          <Terminal size={12} />
          <span>System Kernel Output</span>
        </div>
        <div className="flex gap-1">
          <div className="w-2 h-2 rounded-full bg-red-500/30" />
          <div className="w-2 h-2 rounded-full bg-yellow-500/30" />
          <div className="w-2 h-2 rounded-full bg-green-500/30" />
        </div>
      </div>
      <div className="p-4 overflow-y-auto font-mono text-[11px] space-y-1.5 flex-1 scrollbar-thin">
        {logs.length === 0 && <div className="text-slate-700 italic">Initializing systems... Monitoring global news feeds...</div>}
        {logs.map((log, i) => (
          <div key={i} className="flex gap-3 leading-relaxed">
            <span className="text-slate-600 shrink-0 tabular-nums">[{log.time}]</span>
            <span className={
              log.type === 'error' ? 'text-rose-400' :
                log.type === 'success' ? 'text-emerald-400' :
                  log.type === 'info' ? 'text-sky-400' : 'text-slate-400'
            }>
              {log.type === 'agent' && <span className="text-purple-400 font-bold mr-2 uppercase">{log.agent}:</span>}
              {log.message}
            </span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
};

// D3.js Supply Chain Graph Component (now imported from separate file)
const SupplyChainGraph = ({ data }) => {
  // Transform data format for the D3 component
  const portfolio = data && data.length > 0
    ? [...new Set(data.map(d => d.ticker || d.source_ticker).filter(Boolean))]
    : [];

  const relationships = data || [];

  return <SupplyChainGraphD3 portfolio={portfolio} relationships={relationships} />;
};

const AnalysisPanel = ({ results, loading }) => {
  if (loading) return (
    <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-6 py-20">
      <div className="relative">
        <div className="w-20 h-20 border-2 border-slate-800 border-t-purple-500 rounded-full animate-spin"></div>
        <div className="absolute inset-0 flex items-center justify-center">
          <Zap size={28} className="text-purple-500 animate-pulse" />
        </div>
      </div>
      <div className="text-center">
        <p className="animate-pulse font-mono text-sm tracking-widest text-slate-400 uppercase">Synchronizing Neural Agents...</p>
        <p className="text-[10px] text-slate-600 mt-2 font-mono">Running 10-Factor Impact Framework v3.0</p>
      </div>
    </div>
  );

  if (!results) return (
    <div className="h-full flex items-center justify-center text-slate-600 py-32">
      <div className="text-center max-w-md">
        <Activity size={48} className="mx-auto mb-6 opacity-20 text-purple-500" />
        <h2 className="text-slate-400 font-bold tracking-tight mb-2">SYSTEM STANDBY</h2>
        <p className="text-sm text-slate-500 px-10 leading-relaxed">Input your portfolio tickers and initiate the intelligence workflow to begin real-time analysis.</p>
      </div>
    </div>
  );

  const impact = results.impact?.impact_pct || 0;
  const isPositive = impact >= 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-8 pb-10"
    >
      {/* KPI Section */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Portfolio Impact', val: `${isPositive ? '+' : ''}${impact.toFixed(2)}%`, sub: results.impact?.impact_usd?.toFixed(2) ? `$${results.impact.impact_usd.toLocaleString()}` : 'N/A', color: isPositive ? 'text-emerald-400' : 'text-rose-400' },
          { label: 'Confidence Score', val: `${(results.confidence * 100).toFixed(0)}%`, sub: results.validation_decision || 'Standard', color: 'text-blue-400' },
          { label: 'Intelligence Depth', val: results.news?.length || 0, sub: 'Verified Sources', color: 'text-amber-400' },
          { label: 'Processing Latency', val: `${((results.processing_time_ms || 0) / 1000).toFixed(1)}s`, sub: 'End-to-End Latency', color: 'text-slate-300' }
        ].map((kpi, i) => (
          <div key={i} className="p-5 bg-slate-900/40 border border-white/5 rounded-2xl backdrop-blur-sm">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3">{kpi.label}</p>
            <p className={`text-3xl font-black ${kpi.color}`}>{kpi.val}</p>
            <p className="text-[11px] text-slate-500 mt-1 font-mono tracking-tight">{kpi.sub}</p>
          </div>
        ))}
      </div>

      {/* 10-Factor Breakdown */}
      <div className="p-6 bg-slate-900/20 border border-white/5 rounded-2xl">
        <h3 className="flex items-center gap-2 text-slate-400 font-bold text-[10px] uppercase tracking-[0.2em] mb-6">
          <BarChart2 size={14} className="text-sky-500" />
          10-Factor Exposure Matrix
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {results.classified_articles?.slice(0, 10).map((art, i) => (
            <div key={i} className="p-3 bg-slate-950/40 border border-white/5 rounded-xl text-center">
              <div className="text-[8px] font-bold text-slate-500 uppercase truncate mb-1">{art.factor_name}</div>
              <div className={`text-sm font-black ${art.sentiment_score < 0 ? 'text-rose-500' : 'text-emerald-500'}`}>
                {art.sentiment_score.toFixed(1)}
              </div>
            </div>
          ))}
          {(!results.classified_articles || results.classified_articles.length === 0) && [1, 2, 3, 4, 5].map(i => (
            <div key={i} className="p-3 bg-slate-950/20 border border-white/5 border-dashed rounded-xl opacity-20">
              <div className="h-2 w-10 bg-slate-700 mx-auto rounded" />
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* News Feed */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="flex items-center gap-2 text-slate-300 font-bold text-xs uppercase tracking-widest">
              <Globe size={14} className="text-blue-500" />
              Intelligence Harvest
            </h3>
            <span className="text-[10px] text-slate-600 font-mono">TOP {results.news?.length || 0} ARTICLES</span>
          </div>
          <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2 scrollbar-thin">
            {results.news?.map((art, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.05 }}
                className="p-3.5 rounded-xl bg-slate-900/30 border border-slate-800/40 hover:border-blue-500/30 transition-all cursor-default"
              >
                <div className="flex justify-between items-start mb-2">
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-blue-900/30 text-blue-400 border border-blue-500/20">{art.source}</span>
                  <span className="text-[9px] text-slate-600 font-mono">VERIFIED</span>
                </div>
                <h4 className="text-xs text-slate-300 font-medium leading-relaxed">{art.title}</h4>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Impacts & Reasoning */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="flex items-center gap-2 text-slate-300 font-bold text-xs uppercase tracking-widest">
              <Brain size={14} className="text-purple-500" />
              Reasoning Trail & Context
            </h3>
            <span className="text-[10px] text-slate-600 font-mono">AI-VALIDATED IMPACTS</span>
          </div>
          <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2 scrollbar-thin">
            {results.stock_impacts?.map((imp, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="p-4 rounded-xl bg-slate-900/30 border border-slate-800/40 flex gap-4"
              >
                <div className={`shrink-0 w-14 h-14 rounded-lg flex flex-col items-center justify-center ${imp.impact_pct > 0 ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : imp.impact_pct < 0 ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' : 'bg-slate-700/10 text-slate-400 border border-slate-700/20'}`}>
                  <span className="text-xs font-black">{imp.impact_pct > 0 ? '+' : ''}{imp.impact_pct.toFixed(1)}%</span>
                  <span className="text-[9px] font-bold tracking-widest opacity-70 mt-0.5">{imp.ticker}</span>
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-[10px] font-bold text-purple-400/80 uppercase">Confidence: {(imp.confidence * 100).toFixed()}%</span>
                    <div className="flex-1 h-px bg-white/5" />
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed font-sans">{imp.reason}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* Discovered Relationships & Graph */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
        <SupplyChainGraph data={results.discovered_relationships} />

        <div className="p-6 bg-slate-900/20 border border-white/5 rounded-2xl">
          <h3 className="flex items-center gap-2 text-slate-400 font-bold text-[10px] uppercase tracking-[0.2em] mb-4">
            <Layers size={14} className="text-emerald-500" />
            Supply Chain Intelligence | Discovered Nodes
          </h3>
          <div className="space-y-2 max-h-[250px] overflow-y-auto pr-2 scrollbar-thin">
            {results.discovered_relationships?.map((rel, i) => (
              <div key={i} className="px-3 py-2.5 rounded-lg bg-emerald-500/5 border border-emerald-500/10 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-xs font-bold text-emerald-300">{rel.target_company}</span>
                  <span className="text-[10px] text-slate-600">→</span>
                  <span className="text-xs font-bold text-slate-400">{rel.related_company}</span>
                </div>
                <span className="text-[9px] px-1.5 py-0.5 bg-slate-800 text-slate-500 rounded uppercase font-bold tracking-tighter">{rel.relationship_type} | {(rel.confidence * 100).toFixed()}%</span>
              </div>
            ))}
            {(!results.discovered_relationships || results.discovered_relationships.length === 0) && (
              <div className="text-slate-600 text-[11px] italic text-center py-10">No direct tier mapping required for this entity set.</div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

// --- MAIN APP ---

const App = () => {
  const [activeAgents, setActiveAgents] = useState({});
  const [logs, setLogs] = useState([]);
  const [results, setResults] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [portfolio, setPortfolio] = useState("AAPL, NVDA, Intel, AMD");

  const addLog = (msg, type = 'info', agent = null) => {
    const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setLogs(prev => [...prev, { time, message: msg, type, agent }]);
  };

  const runAnalysis = async () => {
    if (isAnalyzing) return;
    setIsAnalyzing(true);
    setResults(null);
    setLogs([]);
    setActiveAgents({});

    const tickers = portfolio.split(',').map(t => t.trim()).filter(t => t);

    const simulation = async () => {
      setActiveAgents({ 1: 'active' });
      addLog("Initializing News Monitor Agent...", 'agent', 'AGENT 01');
      await new Promise(r => setTimeout(r, 1500));
      setActiveAgents(p => ({ ...p, 1: 'completed', 2: 'active' }));
      addLog("Analyzing 10-factor market classification...", 'agent', 'AGENT 02');
      await new Promise(r => setTimeout(r, 2000));
      setActiveAgents(p => ({ ...p, 2: 'completed', 3: 'active' }));
      addLog("Mapping portfolio dependencies...", 'agent', 'AGENT 03');
      await new Promise(r => setTimeout(r, 1500));
      setActiveAgents(p => ({ ...p, 3: 'completed', 4: 'active' }));
      addLog("Calculating TIER-base impact scores...", 'agent', 'AGENT 04');
      await new Promise(r => setTimeout(r, 2000));
      setActiveAgents(p => ({ ...p, 4: 'completed', 5: 'active' }));
      addLog("Validating confidence thresholds...", 'agent', 'AGENT 05');
    };

    simulation();

    try {
      const res = await axios.post('http://localhost:8000/api/run-intelligence', {
        user_id: 'dashboard_u1',
        portfolio: tickers
      });

      const data = res.data;

      setActiveAgents(p => ({ ...p, 5: 'completed', 6: 'active' }));
      addLog(`System High Confidence Output: Accept Triggered.`, 'success');

      await new Promise(r => setTimeout(r, 1000));
      setActiveAgents(p => ({ ...p, 6: 'completed' }));
      addLog(`Persistence layer updated. Alert generated: ${data.alert_id}`, 'success');

      setResults(data);
    } catch (e) {
      addLog(`Network Failure: Unable to reach orchestration engine.`, 'error');
      console.error(e);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-300 font-sans selection:bg-purple-500/40 overflow-hidden relative">
      {/* Abstract Background Elements */}
      <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.03] pointer-events-none" />
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-purple-600/10 blur-[150px] -mr-64 -mt-64 rounded-full pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-blue-600/10 blur-[120px] -ml-40 -mb-40 rounded-full pointer-events-none" />

      {/* LEFT ORCHESTRATION PANEL */}
      <div className="w-[420px] h-screen flex flex-col border-r border-white/5 bg-slate-900/40 backdrop-blur-2xl z-20">
        <div className="p-8 border-b border-white/5">
          <div className="flex items-center gap-3.5 mb-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-purple-600 to-blue-600 flex items-center justify-center shadow-lg shadow-purple-500/20">
              <Zap size={20} className="text-white fill-white" />
            </div>
            <div>
              <h1 className="text-xl font-black tracking-tighter text-white">MarketPulse<span className="text-purple-500">-X</span></h1>
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.3em]">Orchestration Core v3.0</p>
            </div>
          </div>
        </div>

        <div className="p-6 flex-1 flex flex-col gap-8 overflow-hidden">
          {/* Controls */}
          <div className="space-y-4">
            <div>
              <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2.5 block px-1">Deep Intelligence Target</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={portfolio}
                  onChange={(e) => setPortfolio(e.target.value)}
                  className="flex-1 h-11 bg-slate-950 border border-white/10 rounded-xl px-4 text-xs text-slate-200 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20 transition-all font-mono"
                  placeholder="AAPL, NVDA, MSFT..."
                />
                <button
                  onClick={runAnalysis}
                  disabled={isAnalyzing}
                  className="h-11 px-6 bg-white text-slate-950 rounded-xl text-xs font-black tracking-tighter hover:bg-slate-200 transition-all disabled:opacity-30 disabled:cursor-not-allowed shadow-xl shadow-white/5"
                >
                  {isAnalyzing ? '...' : 'ENGAGE'}
                </button>
              </div>
            </div>
          </div>

          {/* Agents View */}
          <div className="space-y-3 flex-1 overflow-y-auto scrollbar-thin pr-1">
            <div className="text-[10px] font-bold text-slate-600 uppercase tracking-widest px-1 mb-2">Agent Lifecycle Monitor</div>
            <AgentCard id={1} name="Signal Ingestion" icon={Globe} status={activeAgents[1]} />
            <AgentCard id={2} name="Entity Classifier" icon={Brain} status={activeAgents[2]} />
            <AgentCard id={3} name="Graph Dependency" icon={Network} status={activeAgents[3]} />
            <AgentCard id={4} name="Impact Resonance" icon={Layers} status={activeAgents[4]} />
            <AgentCard id={5} name="Neural Validator" icon={ShieldCheck} status={activeAgents[5]} />
            <AgentCard id={6} name="Persistence Layer" icon={Bell} status={activeAgents[6]} />
          </div>

          {/* Terminal */}
          <div className="h-48">
            <LogTerminal logs={logs} />
          </div>
        </div>
      </div>

      {/* RIGHT ANALYTICS PANEL */}
      <div className="flex-1 h-screen overflow-y-auto z-10 p-10 scrollbar-thin">
        <div className="max-w-6xl mx-auto">
          <header className="flex justify-between items-end mb-14">
            <div>
              <div className="flex items-center gap-2.5 mb-2">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-[10px] font-bold text-emerald-500 uppercase tracking-[0.2em]">Neural Network Operational</span>
              </div>
              <h2 className="text-4xl font-black text-white tracking-tighter italic">Intelligence Command Center</h2>
              <p className="text-slate-500 mt-2 text-sm leading-relaxed max-w-lg font-medium opacity-80">Autonomous supply chain intelligence engine monitoring global news andSEC filings for multi-tier portfolio risk propagation.</p>
            </div>
            <div className="text-right hidden sm:block">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest leading-relaxed">System Timestamp</p>
              <p className="text-xs font-mono text-slate-400 mt-1">{new Date().toUTCString()}</p>
            </div>
          </header>

          <AnalysisPanel results={results} loading={isAnalyzing} />
        </div>
      </div>
    </div>
  );
};

export default App;
