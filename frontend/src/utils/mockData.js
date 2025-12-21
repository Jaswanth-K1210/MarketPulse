// Mock data for the dashboard
export const mockPortfolio = {
  user: { name: "Jaswanth", role: "Portfolio Manager" },
  holdings: [
    { id: 1, company: "Apple Inc.", ticker: "AAPL", quantity: 150, purchasePrice: 145.50, currentPrice: 198.75, impact: -2.4 },
    { id: 2, company: "NVIDIA Corporation", ticker: "NVDA", quantity: 80, purchasePrice: 420.00, currentPrice: 875.50, impact: -1.8 },
    { id: 3, company: "Advanced Micro Devices", ticker: "AMD", quantity: 120, purchasePrice: 95.00, currentPrice: 168.30, impact: 0 },
    { id: 4, company: "Intel Corporation", ticker: "INTC", quantity: 200, purchasePrice: 42.50, currentPrice: 36.45, impact: 1.2 },
    { id: 5, company: "Broadcom Inc.", ticker: "AVGO", quantity: 60, purchasePrice: 540.00, currentPrice: 795.20, impact: -0.5 },
  ],
  totalValue: 150000,
  totalChange: 12500,
  changePercent: 8.3
};

export const mockAlerts = [
  {
    id: "alert_1",
    title: "Major Supplier Disruption",
    company: "Apple Inc.",
    ticker: "AAPL",
    severity: "critical",
    impact: -2.4,
    description: "Key semiconductor supplier TSMC reports production delays affecting Q2 shipments",
    timestamp: "2 hours ago",
    confidence: 0.92,
    recommendation: "HOLD",
    impactChain: {
      level1: "TSMC production halt",
      level2: "Apple chip supply reduced",
      level3: "Expected -2.4% impact on AAPL price"
    },
    sources: ["Reuters: TSMC Production Halt", "Bloomberg: Semiconductor Supply"]
  },
  {
    id: "alert_2",
    title: "Regulatory Announcement",
    company: "Tesla Inc.",
    ticker: "TSLA",
    severity: "high",
    impact: 1.8,
    description: "EU approves new EV subsidies that could boost European sales significantly",
    timestamp: "4 hours ago",
    confidence: 0.87,
    recommendation: "BUY",
    impactChain: {
      level1: "EU EV subsidy approved",
      level2: "Tesla European sales potential increases",
      level3: "Expected +1.8% uplift"
    },
    sources: ["EU Official: Subsidy Approval"]
  },
  {
    id: "alert_3",
    title: "Partnership Expansion",
    company: "Microsoft Corp.",
    ticker: "MSFT",
    severity: "medium",
    impact: 0.9,
    description: "Strategic cloud partnership announced with major healthcare network",
    timestamp: "6 hours ago",
    confidence: 0.79,
    recommendation: "MONITOR",
    impactChain: {
      level1: "MSFT cloud partnership",
      level2: "Enterprise revenue stream expands",
      level3: "Expected +0.9% uplift"
    },
    sources: ["MSFT Press Release"]
  }
];

export const mockStats = {
  activeAlerts: 12,
  alertsToday: 3,
  watchedCompanies: 24,
  companiesThisWeek: 2,
  marketImpactScore: 7.2,
  scoreChange: 0.5,
  eventsDetected: 156,
  eventsThisWeek: 28,
  alertTrendData: [
    { day: "Mon", alerts: 8 },
    { day: "Tue", alerts: 12 },
    { day: "Wed", alerts: 15 },
    { day: "Thu", alerts: 18 },
    { day: "Fri", alerts: 12 },
    { day: "Sat", alerts: 9 },
    { day: "Sun", alerts: 7 }
  ]
};

export const mockTriggerArticle = {
  title: "TSMC announces temporary production halt due to power outage",
  source: "Reuters",
  publishedAt: new Date().toISOString(),
  content: "Taiwan Semiconductor Manufacturing Company (TSMC) has announced a temporary production halt affecting all chip production facilities. The halt will affect shipments to major customers including Apple Inc. and NVIDIA Corporation. Analysts say the disruption may take several weeks to resolve.",
  companies: ["TSMC", "Apple Inc.", "NVIDIA Corporation"]
};

export const mockCascadeResult = {
  article: mockTriggerArticle,
  validated: true,
  relationships: [
    { from: "TSMC", to: "Apple Inc.", type: "supplier", confidence: 0.95 },
    { from: "TSMC", to: "NVIDIA Corporation", type: "supplier", confidence: 0.92 }
  ],
  cascade: {
    level1: "TSMC production halt announced",
    level2: "Apple and NVIDIA semiconductor supply disrupted",
    level3: "Portfolio impact: -2.4% AAPL, -1.8% NVDA"
  },
  affectedHoldings: [
    { company: "Apple Inc.", ticker: "AAPL", impact: -2.4, confidence: 0.92 },
    { company: "NVIDIA Corporation", ticker: "NVDA", impact: -1.8, confidence: 0.89 }
  ],
  explanation: "TSMC is a critical supplier to both Apple and NVIDIA. A production halt will reduce semiconductor availability within 2-4 weeks. Historical data shows 1-3% price impact for major customers during similar disruptions. We recommend monitoring developments and considering a partial position reduction if the halt extends beyond 4 weeks.",
  recommendation: "HOLD / MONITOR"
};

export const useAlertTrend = () => {
  return mockStats.alertTrendData;
};
