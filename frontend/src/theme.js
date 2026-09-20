/**
 * MarketPulse Design Tokens — Single source of truth.
 *
 * "Ops-center" terminal aesthetic (World Monitor family): near-black ground,
 * hairline-bordered panels, monospace numerics, one green live/accent colour.
 */

// ── Dark theme (default) ──────────────────────────────────────────────────
const dark = {
  // Backgrounds
  bg:          '#0a0a0a',
  bgDeep:      '#050505',
  panel:       '#101010',
  card:        '#141414',
  cardHover:   '#1a1a1a',
  elevated:    '#1f1f1f',

  // Borders — hairlines carry structure
  border:      '#2a2a2a',
  borderDim:   '#1c1c1c',
  borderFocus: '#4ade80',

  // Text
  text:        '#f5f5f5',
  muted:       '#9ca3af',
  dim:         '#52525b',
  white:       '#ffffff',

  // Interaction accent: live signal green (World Monitor family)
  blue:        '#4ade80',
  blueSoft:    'rgba(74,222,128,0.10)',
  blueMid:     'rgba(74,222,128,0.22)',

  // Direction. The green family is shared with the accent, red stays reserved.
  green:       '#4ade80',
  greenSoft:   'rgba(74,222,128,0.12)',
  greenMid:    'rgba(74,222,128,0.25)',
  red:         '#f87171',
  redSoft:     'rgba(248,113,113,0.12)',
  redMid:      'rgba(248,113,113,0.25)',

  // Categorical hues — for encoding *kinds*, kept muted so no single one shouts.
  orange:      '#fbbf24',
  orangeSoft:  'rgba(251,191,36,0.12)',
  orangeMid:   'rgba(251,191,36,0.25)',
  purple:      '#c084fc',
  purpleSoft:  'rgba(192,132,252,0.12)',
  purpleMid:   'rgba(192,132,252,0.25)',
  cyan:        '#22d3ee',
  cyanSoft:    'rgba(34,211,238,0.12)',
  cyanMid:     'rgba(34,211,238,0.25)',
  yellow:      '#facc15',
  yellowSoft:  'rgba(250,204,21,0.12)',
  pink:        '#f472b6',
  pinkSoft:    'rgba(244,114,182,0.12)',

  // Flat, not gradients. An instrument panel has no wash on it.
  gradBlue:    '#4ade80',
  gradGreen:   '#4ade80',
  gradRed:     '#f87171',
  gradPurple:  '#c084fc',
  gradCyan:    '#22d3ee',
  gradBrand:   '#4ade80',
}

// ── Export ─────────────────────────────────────────────────────────────────
export const T = dark

// Convenience: grade-specific colors
export const GRADE_COLORS = {
  A: { color: T.green,  bg: T.greenSoft,  border: T.greenMid,  ring: 'rgba(74,222,128,0.35)' },
  B: { color: T.blue,   bg: T.blueSoft,   border: T.blueMid,   ring: 'rgba(74,222,128,0.35)' },
  C: { color: T.orange, bg: T.orangeSoft,  border: T.orangeMid, ring: 'rgba(251,191,36,0.35)' },
  D: { color: T.red,    bg: T.redSoft,    border: T.redMid,    ring: 'rgba(248,113,113,0.35)' },
  F: { color: T.red,    bg: T.redSoft,    border: T.redMid,    ring: 'rgba(248,113,113,0.45)' },
}

// Edge type colors for KG
export const EDGE_COLORS = {
  supplier:      T.orange,
  competitor:    T.red,
  customer:      T.green,
  sector_member: T.blue,
  sector_peer:   T.cyan,
  event_affected: T.purple,
  related:       T.muted,
}

// Source type colors for convergence
export const SOURCE_COLORS = {
  news:             T.blue,
  technical:        T.green,
  options_flow:     T.purple,
  insider:          T.orange,
  fundamentals:     T.cyan,
  short_interest:   T.red,
  retail_sentiment: T.pink,
  knowledge_graph:  T.yellow,
  memory:           T.muted,
}