import { useState } from "react";
import { motion } from "framer-motion";
import { RefreshCw, Search, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DetailModal } from "./DetailModal";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts";

interface ResultsProps {
  data: any;
  portfolio: string[];
  onReAnalyze: () => void;
}

export function Results({ data, portfolio, onReAnalyze }: ResultsProps) {
  const [selectedAlert, setSelectedAlert] = useState<any>(null);

  // 1. Calculate KPIs (Mock data mostly, enhanced with real when available)
  const activeAlertsCount = data?.stock_impacts?.filter((s: any) => Math.abs(s.impact_pct) > 1.5).length || 0;
  const watchedCompaniesCount = portfolio.length;
  // Use a fixed aesthetic score if data is missing for better demo visualization
  const marketImpactScore = data?.portfolio_total_impact?.total_impact_pct
    ? Math.abs(data.portfolio_total_impact.total_impact_pct).toFixed(1)
    : "7.2";
  const eventsDetectedCount = (data?.classified_articles?.length || 0) + (data?.discovered_relationships?.length || 0);

  // 2. Stock Tickers
  const stockTickers = portfolio.map(ticker => {
    const impact = data?.stock_impacts?.find((s: any) => s.ticker === ticker);
    const pct = impact?.impact_pct || (Math.random() * 2 - 1);
    // Mock Prices for "Real-time" feel
    const basePrice = 150 + Math.random() * 800;
    return {
      symbol: ticker,
      name: getCompanyName(ticker),
      price: basePrice.toFixed(2),
      change: pct,
      isPositive: pct >= 0
    };
  });

  // 3. Main Alert (Detailed Card)
  // We'll construct a rich alert object from the top impact or a mock if loading
  const topImpact = data?.stock_impacts?.sort((a: any, b: any) => Math.abs(b.impact_pct) - Math.abs(a.impact_pct))[0];
  const mainAlert = topImpact ? {
    title: `${Math.abs(topImpact.impact_pct) > 2 ? 'HIGH' : 'MEDIUM'}: ${getCompanyName(topImpact.ticker)} Event`,
    date: new Date().toLocaleString(),
    impact: `${topImpact.impact_pct > 0 ? '+' : ''}${topImpact.impact_pct.toFixed(2)}%`,
    confidence: `${(data.confidence_score * 100).toFixed(0)}%`,
    holdings: getCompanyName(topImpact.ticker),
    holdingValue: "+1.0% (+$418.11)", // Mock P&L
    reasoning: topImpact.reason,
    severity: Math.abs(topImpact.impact_pct) > 2 ? "HIGH" : "MEDIUM"
  } : {
    title: "MEDIUM: Apple Inc. Event",
    date: "12/12/2025, 23:29:56",
    impact: "+0.38%",
    confidence: "80%",
    holdings: "Apple Inc.",
    holdingValue: "+1.0% (+$418.11)",
    reasoning: "Apple receives partial legal relief in Epic appeals ruling. This positive news directly affects Apple with an estimated 1.0% impact.",
    severity: "MEDIUM"
  };

  // 4. Chart Data
  const chartData = [
    { day: "Mon", alerts: 0 },
    { day: "Tue", alerts: 0 },
    { day: "Wed", alerts: 0 },
    { day: "Thu", alerts: 0 },
    { day: "Fri", alerts: 1 },
    { day: "Sat", alerts: 2 },
    { day: "Sun", alerts: activeAlertsCount },
  ];

  return (
    <div className="max-w-[1600px] mx-auto space-y-6 text-white font-sans">

      {/* HEADER ROW */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-display font-bold text-white mb-2">Dashboard</h1>
          <p className="text-sm text-gray-400 flex items-center gap-2">
            Real-time market intelligence at a glance <span className="flex h-2 w-2 rounded-full bg-green-500 box-shadow-green animate-pulse" /> <span className="text-green-500 font-bold">Live</span>
            <span className="text-gray-600 ml-2">Auto-Refresh Every 5 Min</span>
          </p>
        </div>

        {/* Search Bar */}
        <div className="flex items-center gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search companies, events..."
              className="bg-[#141820] border border-white/5 rounded-lg pl-10 pr-4 py-2 w-80 text-sm text-white focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>
          <button onClick={onReAnalyze} className="p-2 rounded-lg bg-[#141820] border border-white/5 hover:bg-white/5 transition-colors">
            <RefreshCw className="w-5 h-5 text-gray-400" />
          </button>
        </div>
      </div>

      {/* 1. STOCK TICKER ROW */}
      <div className="flex items-center justify-between mb-2">
        <h3 className="flex items-center gap-2 text-lg font-bold text-white">
          <span className="text-blue-500">~</span> Live Stock Prices
        </h3>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span>Updated 0s ago</span>
          <button className="px-3 py-1 bg-blue-500/10 text-blue-400 rounded hover:bg-blue-500/20 transition-colors">Refresh Prices</button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {stockTickers.map((stock) => (
          <div
            key={stock.symbol}
            className="bg-[#0f1218] p-4 rounded-xl border border-white/5 relative overflow-hidden group"
          >
            <div className="flex justify-between items-start mb-3">
              <div>
                <span className="block font-bold text-sm text-gray-300">{stock.symbol} •</span>
                <span className="block text-xs text-gray-500 truncate max-w-[100px]">{stock.name}</span>
              </div>
            </div>
            <div className="flex justify-between items-end">
              <span className="text-xl font-bold font-mono text-white">${stock.price}</span>
              <span className={`text-[10px] font-bold px-2 py-1 rounded-full ${stock.isPositive ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>
                {stock.isPositive ? '+' : ''}{stock.change.toFixed(2)}%
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* 2. KPI METRICS ROW */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
        <MetricCard
          title="Active Alerts"
          value={activeAlertsCount}
          subtext="+0 today"
          subtextColor="text-red-500"
          icon={<div className="text-red-500">!</div>}
          borderColor="border-l-4 border-l-red-500" // Highlight style
        />
        <MetricCard
          title="Watched Companies"
          value={watchedCompaniesCount}
          subtext="+0 this week"
          subtextColor="text-green-500"
          icon={<div className="text-blue-500">🏢</div>}
        />
        <MetricCard
          title="Market Impact Score"
          value={marketImpactScore}
          subtext="+0.5 from yesterday"
          subtextColor="text-green-500"
          icon={<div className="text-green-500">📈</div>}
        />
        <MetricCard
          title="Events Detected"
          value={eventsDetectedCount}
          subtext="+0 this week"
          subtextColor="text-gray-500"
          icon={<div className="text-yellow-500">⚡</div>}
        />
      </div>

      {/* 3. MAIN SPLIT SECTION */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">

        {/* LEFT: DETAILED ALERTS CHECKLIST (2/3) */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold flex items-center gap-2">
              🔔 Recent Alerts
            </h3>
            <a href="#" className="text-blue-500 text-sm hover:underline">View all</a>
          </div>

          {/* Specific Card Style from Screenshot */}
          <div className="bg-[#0f1218] border-l-4 border-l-yellow-500 rounded-r-xl border-y border-r border-[#ffffff10] p-6 relative overflow-hidden">
            <div className="flex justify-between items-start mb-6">
              <div className="flex gap-3">
                <div className="mt-1 text-yellow-500">⚠️</div>
                <div>
                  <h4 className="text-lg font-bold text-white">{mainAlert.title}</h4>
                  <p className="text-xs text-gray-500 font-mono">{mainAlert.date}</p>
                </div>
              </div>
              <span className="px-3 py-1 bg-green-900/30 text-green-500 text-xs font-bold rounded uppercase tracking-wider border border-green-500/20">LOW</span>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-[#161b22] p-4 rounded-lg">
                <span className="text-xs text-gray-400 block mb-1">Portfolio Impact</span>
                <span className="text-xl font-bold text-green-400">{mainAlert.impact}</span>
              </div>
              <div className="bg-[#161b22] p-4 rounded-lg">
                <span className="text-xs text-gray-400 block mb-1">Confidence</span>
                <span className="text-xl font-bold text-blue-400">{mainAlert.confidence}</span>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <h5 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">📦 Affected Holdings:</h5>
                <div className="flex justify-between items-center bg-[#161b22] px-4 py-3 rounded">
                  <span className="font-medium text-gray-300">{mainAlert.holdings}</span>
                  <span className="text-green-500 font-mono text-sm">{mainAlert.holdingValue}</span>
                </div>
              </div>

              <div>
                <h5 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">⛓️ Supply Chain:</h5>
                <div className="bg-[#161b22] px-4 py-3 rounded text-gray-400 text-sm">
                  → →
                </div>
              </div>

              <div>
                <h5 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">📊 Analysis:</h5>
                <div className="bg-[#161b22]/50 p-3 rounded text-sm text-gray-300 leading-relaxed border border-white/5">
                  {mainAlert.reasoning}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT: NEWS STATUS & CHART (1/3) */}
        <div className="space-y-6">
          {/* 1. News Updated Status Card */}
          <div className="bg-[#11141a] rounded-xl border border-white/10 p-5 shadow-2xl">
            <h3 className="font-bold text-white mb-4 flex items-center gap-2">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" /> News Updated
            </h3>
            <div className="space-y-3">
              <StatusItem label={`Last fetch: ${new Date().toLocaleString()}`} />
              <StatusItem label={`Found: ${data?.news?.length || 0} articles across 4 sources`} />
              <StatusItem label={`Processing time: ${data?.processing_time_ms ? (data.processing_time_ms / 1000).toFixed(0) : 0}s`} />
            </div>
            <div className="w-full h-1 bg-gray-800 mt-4 rounded-full overflow-hidden">
              <div className="h-full bg-blue-500 w-full animate-[progress_2s_ease-in-out]" />
            </div>
          </div>

          {/* 2. Alert Trend Chart */}
          <div className="bg-[#0f1218] rounded-xl border border-white/5 p-6 h-[300px]">
            <h3 className="font-bold text-white mb-6 text-sm">Alert Trend (7 days)</h3>
            <div className="h-[200px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                  <XAxis dataKey="day" stroke="#444" fontSize={10} tickLine={false} axisLine={false} />
                  <YAxis stroke="#444" fontSize={10} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#000', border: '1px solid #333' }}
                    itemStyle={{ color: '#fff' }}
                  />
                  <Line type="monotone" dataKey="alerts" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3, fill: "#3b82f6" }} activeDot={{ r: 5 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* DETAIL MODAL (Hidden by default) */}
      <DetailModal
        isOpen={!!selectedAlert}
        onClose={() => setSelectedAlert(null)}
        alert={selectedAlert}
        graphData={{ nodes: [], links: [] }}
      />
    </div>
  );
}

// --- SUB COMPONENTS ---

function MetricCard({ title, value, subtext, subtextColor, icon, borderColor = "border border-white/5" }: any) {
  return (
    <div className={`bg-[#0f1218] p-5 rounded-xl ${borderColor} relative group`}>
      <div className="flex justify-between items-start mb-4">
        <div>
          <h4 className="text-gray-400 text-sm font-medium">{title}</h4>
          <div className="text-3xl font-bold text-white mt-1">{value}</div>
        </div>
        <div className="p-2 rounded-lg bg-[#ffffff05] border border-[#ffffff05] group-hover:border-white/10 transition-colors">
          {icon}
        </div>
      </div>
      <p className={`text-xs ${subtextColor} font-bold`}>{subtext}</p>
    </div>
  )
}

function StatusItem({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-gray-400">
      <CheckCircle2 className="w-4 h-4 text-green-500" />
      <span>{label}</span>
    </div>
  )
}

function getCompanyName(ticker: string) {
  const map: Record<string, string> = {
    "AAPL": "Apple Inc.",
    "NVDA": "NVIDIA Corporation",
    "AMD": "Advanced Micro Devices",
    "INTC": "Intel Corporation",
    "AVGO": "Broadcom Inc.",
    "TSM": "Taiwan Semiconductor"
  };
  return map[ticker] || ticker;
}
