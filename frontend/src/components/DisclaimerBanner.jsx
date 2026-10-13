import { DISCLAIMER } from '../utils/disclaimer'

export default function DisclaimerBanner() {
  return (
    <div
      role="note"
      aria-label="Regulatory disclaimer"
      style={{
        background: 'rgba(255,193,7,0.08)',
        borderTop: '1px solid rgba(255,193,7,0.2)',
        padding: '4px 12px',
        fontSize: '10px',
        color: 'rgba(255,193,7,0.7)',
        textAlign: 'center',
        lineHeight: '1.4',
        flexShrink: 0,
      }}
    >
      {/* Full text from sm up; on phones it collapses so it doesn't eat the viewport. */}
      <span className="hidden sm:inline">{DISCLAIMER}</span>
      <details className="sm:hidden">
        <summary>Not investment advice. Tap for details.</summary>
        {DISCLAIMER}
      </details>
    </div>
  )
}
