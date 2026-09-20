import React, { useEffect, useMemo, useState } from 'react'
import { X, Search, Building2, Users, Newspaper, TrendingUp, Shield, Ship, AlertCircle } from 'lucide-react'
import { T as C } from '../theme'
import { getCountry } from '../services/api'

const SECTION_META = {
  companies: { label: 'Companies',        icon: Building2 },
  insiders:  { label: 'Insider Filings',  icon: Users },
  news:      { label: 'News',             icon: Newspaper },
  markets:   { label: 'Markets',          icon: TrendingUp },
  tensions:  { label: 'Military Tensions', icon: Shield },
  shipping:  { label: 'Shipping Lanes',   icon: Ship },
}

/** A section with no live source states why. An empty card would read as calm. */
function Unavailable({ reason }) {
  return (
    <div className="flex items-start gap-2 px-3 py-2.5" style={{ background: 'rgba(251,191,36,0.06)', border: `1px solid ${C.orange}33` }}>
      <AlertCircle size={13} style={{ color: C.orange, marginTop: 1, flexShrink: 0 }} />
      <div>
        <div className="text-[10px] font-semibold" style={{ color: C.orange }}>Source unavailable</div>
        <div className="text-[10px] mt-0.5 leading-relaxed" style={{ color: C.muted }}>{reason}</div>
      </div>
    </div>
  )
}

function Section({ id, section, children }) {
  const { label, icon: Icon } = SECTION_META[id]
  return (
    <div className="mb-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon size={13} style={{ color: section.available ? C.blue : C.dim }} />
        <span className="text-[11px] font-semibold" style={{ color: C.text }}>{label}</span>
        <span className="w-1.5 h-1.5 rounded-full" style={{ background: section.available ? C.green : C.red }} />
        {section.note && (
          <span className="text-[9px] ml-auto" style={{ color: C.dim }}>{section.note}</span>
        )}
      </div>
      {section.available ? children : <Unavailable reason={section.error || 'no reason reported'} />}
    </div>
  )
}

export default function CountryPanel({ iso2, name, onClose, onCompanyClick }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState('')

  useEffect(() => {
    if (!iso2) return
    setLoading(true); setData(null); setFilter('')
    getCountry(iso2).then(setData).catch(() => setData(null)).finally(() => setLoading(false))
  }, [iso2])

  const companies = data?.sections?.companies?.data || []
  const visible = useMemo(() => {
    const q = filter.trim().toUpperCase()
    if (!q) return companies
    return companies.filter(c =>
      c.ticker.toUpperCase().includes(q) || (c.name || '').toUpperCase().includes(q))
  }, [companies, filter])

  if (!iso2) return null
  const cov = data?.coverage

  return (
    <div className="fixed top-0 right-0 h-full overflow-y-auto z-50 border-l"
      style={{ width: 380, background: C.panel, borderColor: C.border }}>

      <div className="sticky top-0 px-4 py-3 border-b flex items-center gap-2"
        style={{ background: C.panel, borderColor: C.border }}>
        <div className="min-w-0">
          <div className="text-sm font-semibold truncate" style={{ color: C.text }}>
            {data?.country?.name || name || iso2}
          </div>
          {cov && (
            <div className="text-[10px]" style={{ color: cov.live_count < cov.total_count ? C.orange : C.green }}>
              {cov.live_count}/{cov.total_count} sections live
            </div>
          )}
        </div>
        <button onClick={onClose} className="ml-auto p-1.5 hover:bg-white/5">
          <X size={16} style={{ color: C.muted }} />
        </button>
      </div>

      <div className="p-4">
        {loading && <div className="text-[11px]" style={{ color: C.muted }}>Loading {iso2}…</div>}
        {!loading && !data && (
          <div className="text-[11px]" style={{ color: C.red }}>Could not load country intelligence.</div>
        )}

        {data && (
          <>
            <Section id="companies" section={data.sections.companies}>
              {companies.length === 0 ? (
                <div className="text-[10px]" style={{ color: C.dim }}>
                  No tracked company is domiciled here.
                </div>
              ) : (
                <>
                  <div className="relative mb-2">
                    <Search size={12} style={{ color: C.dim, position: 'absolute', left: 8, top: 8 }} />
                    <input value={filter} onChange={e => setFilter(e.target.value)}
                      placeholder="Filter companies in this country"
                      className="w-full pl-7 pr-2 py-1.5 text-[11px] outline-none"
                      style={{ background: C.card, border: `1px solid ${C.border}`, color: C.text }} />
                  </div>
                  {visible.map(c => (
                    <button key={c.ticker} onClick={() => onCompanyClick?.(c.ticker)}
                      className="w-full flex items-center gap-2 px-2 py-1.5 text-left hover:bg-white/5">
                      <span className="text-[11px] font-mono font-semibold" style={{ color: C.blue }}>{c.ticker}</span>
                      <span className="text-[10px] truncate" style={{ color: C.muted }}>{c.name}</span>
                      {c.city && <span className="text-[9px] ml-auto shrink-0" style={{ color: C.dim }}>{c.city}</span>}
                    </button>
                  ))}
                  {visible.length === 0 && (
                    <div className="text-[10px] px-2" style={{ color: C.dim }}>No match for “{filter}”.</div>
                  )}
                </>
              )}
            </Section>

            <Section id="markets" section={data.sections.markets}>
              {(() => {
                const m = data.sections.markets.data || {}
                const up = (m.change_percent ?? 0) >= 0
                return (
                  <div className="px-3 py-2" style={{ background: C.card, border: `1px solid ${C.border}` }}>
                    <div className="text-[10px]" style={{ color: C.muted }}>{m.index}</div>
                    <div className="text-lg font-mono font-semibold" style={{ color: C.text }}>
                      {m.current_price?.toLocaleString?.() ?? '--'}
                    </div>
                    <div className="text-[11px] font-semibold" style={{ color: up ? C.green : C.red }}>
                      {up ? '+' : ''}{m.change_percent}%
                    </div>
                  </div>
                )
              })()}
            </Section>

            <Section id="insiders" section={data.sections.insiders}>
              {(data.sections.insiders.data || []).slice(0, 12).map((t, i) => (
                <div key={i} className="flex items-center gap-2 px-2 py-1 border-b"
                  style={{ borderColor: C.borderDim }}>
                  <span className="text-[10px] font-mono" style={{ color: C.blue }}>{t.ticker}</span>
                  <span className="text-[10px] truncate" style={{ color: C.muted }}>{t.insider_name}</span>
                  <span className="text-[9px] ml-auto font-semibold"
                    style={{ color: t.transaction_type === 'BUY' ? C.green : C.red }}>
                    {t.transaction_type}
                  </span>
                </div>
              ))}
            </Section>

            <Section id="news" section={data.sections.news}>
              {(data.sections.news.data || []).slice(0, 10).map((n, i) => (
                <div key={i} className="px-2 py-1.5 border-b" style={{ borderColor: C.borderDim }}>
                  <div className="text-[10px] leading-snug" style={{ color: C.text }}>{n.title}</div>
                  <div className="text-[9px] mt-0.5" style={{ color: C.dim }}>{n.source}</div>
                </div>
              ))}
              {(data.sections.news.data || []).length === 0 && (
                <div className="text-[10px]" style={{ color: C.dim }}>No news tagged to this country right now.</div>
              )}
            </Section>

            <Section id="tensions" section={data.sections.tensions}>
              <div className="text-[10px]" style={{ color: C.muted }}>
                {(data.sections.tensions.data?.events || []).length} events,{' '}
                {(data.sections.tensions.data?.conflicts || []).length} active conflicts
              </div>
            </Section>

            <Section id="shipping" section={data.sections.shipping}>
              <div />
            </Section>
          </>
        )}
      </div>
    </div>
  )
}
