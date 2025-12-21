// Additional mock data for positive/negative triggers
export const mockPositiveEvent = {
  article: {
    title: "ARM Holdings announces breakthrough GPU architecture",
    source: "TechCrunch",
    publishedAt: new Date().toISOString(),
    content: "ARM Holdings has announced a major breakthrough in GPU architecture that promises 40% better performance efficiency. This development is expected to benefit multiple semiconductor customers including NVIDIA and Broadcom.",
    companies: ["ARM", "NVIDIA", "Broadcom"]
  },
  validated: true,
  relationships: [
    { from: "ARM", to: "NVIDIA Corporation", type: "technology_partner", confidence: 0.94 },
    { from: "ARM", to: "Broadcom Inc.", type: "technology_partner", confidence: 0.91 }
  ],
  cascade: {
    level1: "ARM announces GPU breakthrough",
    level2: "NVIDIA and Broadcom gain competitive advantage",
    level3: "Portfolio impact: +2.8% NVDA, +1.5% AVGO"
  },
  affectedHoldings: [
    { company: "NVIDIA Corporation", ticker: "NVDA", impact: 2.8, confidence: 0.94 },
    { company: "Broadcom Inc.", ticker: "AVGO", impact: 1.5, confidence: 0.91 }
  ],
  explanation: "ARM's GPU breakthrough will enable faster chip designs for both NVIDIA and Broadcom. This technology advance typically results in 1-3% uplift for early adopters. We recommend considering accumulating positions in both stocks.",
  recommendation: "BUY"
};

export const mockNegativeEvent = {
  article: {
    title: "ASML delays next-generation chip equipment shipments",
    source: "Reuters",
    publishedAt: new Date().toISOString(),
    content: "ASML Holding, the critical equipment supplier for semiconductor manufacturers, has announced delays in shipping its next-generation EUV lithography systems. The delay is expected to impact production timelines at TSMC and Samsung.",
    companies: ["ASML", "TSMC", "Samsung"]
  },
  validated: true,
  relationships: [
    { from: "ASML", to: "TSMC", type: "equipment_supplier", confidence: 0.98 },
    { from: "ASML", to: "Samsung Electronics", type: "equipment_supplier", confidence: 0.96 }
  ],
  cascade: {
    level1: "ASML delays equipment shipments",
    level2: "TSMC and Samsung production timelines pushed back",
    level3: "Portfolio impact: -1.8% AAPL, -1.5% NVDA, -1.2% AMD"
  },
  affectedHoldings: [
    { company: "Apple Inc.", ticker: "AAPL", impact: -1.8, confidence: 0.93 },
    { company: "NVIDIA Corporation", ticker: "NVDA", impact: -1.5, confidence: 0.90 },
    { company: "Advanced Micro Devices", ticker: "AMD", impact: -1.2, confidence: 0.87 }
  ],
  explanation: "ASML's equipment delays will push back next-gen chip production at TSMC and Samsung, affecting supply to Apple, NVIDIA, and AMD. Historical data suggests 1-2% impact for 2-3 weeks. Consider defensive positions or hedging strategies.",
  recommendation: "HOLD / REDUCE"
};
