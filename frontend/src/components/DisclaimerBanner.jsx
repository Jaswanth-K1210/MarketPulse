import { DISCLAIMER } from '../utils/disclaimer'

export default function DisclaimerBanner() {
  return (
    <div
      role="note"
      aria-label="Regulatory disclaimer"
      style={{
        background: 'rgba(255,193,7,0.08)',
        borderTop: '1px solid rgba(255,193,7,0.2)',
        padding: '6px 16px',
        fontSize: '11px',
        color: 'rgba(255,193,7,0.7)',
        textAlign: 'center',
        lineHeight: '1.4',
        flexShrink: 0,
      }}
    >
      {DISCLAIMER}
    </div>
  )
}
