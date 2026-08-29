/**
 * MarketPulse Design Tokens — Single source of truth.
 *
 * All components import from here instead of redefining colors.
 * Supports dark/light/grey themes via CSS variables.
 */

// ── Dark theme (default) ──────────────────────────────────────────────────
const dark = {
  // Backgrounds
  bg:          '#0b1221',
  bgDeep:      '#060c18',
  panel:       '#0f1a2e',
  card:        '#131f35',
  cardHover:   '#182540',
  elevated:    '#1a2d4a',

  // Borders
  border:      '#1c2f4a',
  borderDim:   '#152340',
  borderFocus: '#4f91f6',

  // Text
  text:        '#dde8f5',
  muted:       '#5d7a9a',
  dim:         '#243650',
  white:       '#ffffff',

  // Semantic colors
  blue:        '#4f91f6',
  blueSoft:    'rgba(79,145,246,0.10)',
  blueMid:     'rgba(79,145,246,0.20)',
  green:       '#22d18b',
  greenSoft:   'rgba(34,209,139,0.10)',
  greenMid:    'rgba(34,209,139,0.20)',
  red:         '#f06565',
  redSoft:     'rgba(240,101,101,0.10)',
  redMid:      'rgba(240,101,101,0.20)',
  orange:      '#f5a523',
  orangeSoft:  'rgba(245,165,35,0.10)',
  orangeMid:   'rgba(245,165,35,0.20)',
  purple:      '#a07cf5',
  purpleSoft:  'rgba(160,124,245,0.10)',
  purpleMid:   'rgba(160,124,245,0.20)',
  cyan:        '#22d3ee',
  cyanSoft:    'rgba(34,211,238,0.10)',
  yellow:      '#fbbf24',
  yellowSoft:  'rgba(251,191,36,0.10)',
  pink:        '#f472b6',
  pinkSoft:    'rgba(244,114,182,0.10)',

  // Gradients
  gradBlue:    'linear-gradient(135deg, #4f91f6, #818cf8)',
  gradGreen:   'linear-gradient(135deg, #22d18b, #34d399)',
  gradRed:     'linear-gradient(135deg, #f06565, #fb7185)',
  gradPurple:  'linear-gradient(135deg, #a07cf5, #c084fc)',
  gradCyan:    'linear-gradient(135deg, #22d3ee, #67e8f9)',
  gradBrand:   'linear-gradient(135deg, #4f91f6, #a07cf5, #22d3ee)',
}

// ── Export ─────────────────────────────────────────────────────────────────
export const T = dark

// Convenience: grade-specific colors
export const GRADE_COLORS = {
  A: { color: T.green,  bg: T.greenSoft,  border: T.greenMid,  ring: 'rgba(34,209,139,0.35)' },
  B: { color: T.blue,   bg: T.blueSoft,   border: T.blueMid,   ring: 'rgba(79,145,246,0.35)' },
  C: { color: T.orange, bg: T.orangeSoft,  border: T.orangeMid, ring: 'rgba(245,165,35,0.35)' },
  D: { color: T.red,    bg: T.redSoft,    border: T.redMid,    ring: 'rgba(240,101,101,0.35)' },
  F: { color: T.red,    bg: T.redSoft,    border: T.redMid,    ring: 'rgba(240,101,101,0.45)' },
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
