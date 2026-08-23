# MarketPulse: Bloomberg-Like Intelligence Platform Implementation Plan

Based on analysis of BloombergGPT, FinGPT, FinSphere, FinKario, FLARKO, FinRobot, FundaPod, and orchestration framework papers.

---

## Current State Assessment

| Paper Recommendation | Status | What Was Built |
|---|---|---|
| **FinGPT**: Data engineering layer | ✅ DONE | `snr_filter.py` — 6-dimension scoring, rejects noise before LLM |
| **FinGPT**: SEC/filings ingestion | ✅ DONE | `sec_parser.py` + wired into `matcher_discovery` as SOURCE 1 + KG builder |
| **FinGPT**: Finance-specific system prompts | ✅ DONE | `app/ml/prompts.py` — 6 domain-calibrated templates |
| **FinSphere**: Real tools at each node | ✅ DONE | `quant_tools.py` — 6 tools parallel fan-out, `alpha_scorer` tool-first |
| **FinSphere**: AnalyScore quality rubric | ✅ DONE | `quality_evaluator.py` — 5 dimensions, A-F grading |
| **Orchestration**: Memory agent | ✅ DONE | `memory_agent.py` — Redis-backed cross-run temporal memory |
| **Orchestration**: Structured control messages | ✅ DONE | `audit_agent.py` — structured pipeline execution log |
| **Orchestration**: Audit agent | ✅ DONE | `audit_agent.py` — final node, enables "explain this signal" |
| **FinKario**: Dynamic knowledge graph | ✅ DONE | `kg_builder.py` — auto-constructs from SEC/yfinance/gnn/DB |
| **FinKario**: Two-stage retrieval | ✅ DONE | `kg_retriever.py` — BFS traversal + context fetching, wired into discovery |

---

## Complete Pipeline Architecture

```
news_monitor → classifier → quant_tools → alpha_scorer → convergence_detector
                                                                    ↓
                                                            matcher_fast
                                                           ↙            ↘
                                                  discovery (5-source)  skip
                                                       ↓                ↘
                                               impact_calculator ←───────┘
                                                       ↓
                                              confidence_validator
                                               ↙              ↘
                                          loop             alert_generator
                                           ↑                      ↓
                                      news_monitor          memory_store
                                                              ↓
                                                         kg_retrieval
                                                              ↓
                                                         quality_eval
                                                              ↓
                                                          audit_final
                                                              ↓
                                                             END
```

**11 nodes total** (was 9, added 2 new post-alert nodes + rewired 3)

---

## Implementation Log — ALL PHASES COMPLETE

### Phase 1: Data Layer (FinGPT)
- [x] `app/services/data/snr_filter.py` — SNR filter: source tier, recency, content quality, portfolio relevance, dedup
- [x] `app/ml/prompts.py` — 6 domain-calibrated prompt templates
- [x] `app/agents/nodes.py` — SNR filter wired into `agent_1_news_monitor`

### Phase 2: Tool-First Architecture (FinSphere)
- [x] `app/services/data/quant_tools.py` — 6 tools parallel fan-out, composite scoring, LLM formatting
- [x] `app/agents/state.py` — 5 new state fields (quant_tool_data, etc.)
- [x] `app/agents/alpha_scorer.py` — Rewritten: tool-first, 70/30 blend, optional LLM synthesis
- [x] `app/agents/convergence_detector.py` — Rewritten: 7-category signal vectors, contradiction flagging
- [x] `app/agents/workflow.py` — New pipeline: classifier → quant_tools → alpha_scorer
- [x] `app/agents/nodes.py` — `agent_quant_tool_dispatcher` node

### Phase 3: Memory Agent (Orchestration Paper)
- [x] `app/services/memory_agent.py` — Redis-backed: record, query, streak, trend, temporal context
- [x] `app/agents/nodes.py` — `agent_memory_store` node (records signals + builds temporal context)

### Phase 3b: Audit Agent (Orchestration Paper)
- [x] `app/services/audit_agent.py` — Structured audit: per-node timing, tool calls, LLM prompts
- [x] `app/agents/nodes.py` — `agent_audit_final` node (final pipeline node, persists to SQLite)

### Phase 4: Knowledge Graph (FinKario)
- [x] `app/services/kg_builder.py` — Dynamic KG: seeds from gnn/SEC/yfinance/DB, NetworkX + JSON
- [x] `app/services/kg_retriever.py` — Two-stage retrieval: BFS traversal + context fetching
- [x] `app/agents/nodes.py` — `agent_kg_retrieval` node + KG wired as SOURCE 5 in discovery

### Phase 5: Quality Evaluation (FinSphere AnalyScore)
- [x] `app/services/quality_evaluator.py` — 5 dimensions: accuracy, relevance, depth, timeliness, actionability
- [x] `app/agents/nodes.py` — `agent_quality_eval` node

### Wiring
- [x] `app/agents/workflow.py` — 11-node pipeline with post-alert chain
- [x] `app/agents/state.py` — 12 new state fields across memory/KG/quality/audit
- [x] `app/services/relationship_fusion.py` — Added KG + news_context source confidences

---

## Files Created (7)
1. `app/ml/prompts.py` — Centralized finance prompts
2. `app/services/data/quant_tools.py` — Quantitative tool dispatcher
3. `app/services/data/snr_filter.py` — SNR filter
4. `app/services/memory_agent.py` — Redis-backed memory
5. `app/services/audit_agent.py` — Structured audit log
6. `app/services/kg_builder.py` — Dynamic knowledge graph
7. `app/services/kg_retriever.py` — Two-stage KG retrieval
8. `app/services/quality_evaluator.py` — AnalyScore quality rubric

## Files Modified (6)
1. `app/agents/state.py` — 12 new fields
2. `app/agents/workflow.py` — 11-node pipeline
3. `app/agents/nodes.py` — 4 new nodes + KG in discovery + SNR in monitor
4. `app/agents/alpha_scorer.py` — Rewritten tool-first
5. `app/agents/convergence_detector.py` — Rewritten tool-first
6. `app/services/relationship_fusion.py` — Added KG source
