import React, { useState, useEffect } from 'react'
import Watchlist from './Watchlist'
import CompanyDetail from './CompanyDetail'

/**
 * One ticker-centric surface, replacing three tabs that each did part of the job.
 *
 * Search, Watchlist and Company Deep Dive were separate routes with two
 * duplicate ticker inputs between them, and the watchlist's entries were not
 * even clickable. Search only ever fetched /api/stock-prices, so its "company
 * intelligence" report was prices; CompanyDetail fetches the six intelligence
 * endpoints and is the real deep dive.
 *
 * Two states: no ticker selected shows the watchlist as the picker; a selected
 * ticker shows the deep dive. The deep dive carries its own search box, so
 * arriving without a watchlist entry still works.
 */
export default function Research({ initialTicker }) {
  const [ticker, setTicker] = useState(initialTicker || null)

  useEffect(() => {
    if (initialTicker) setTicker(initialTicker)
  }, [initialTicker])

  if (!ticker) {
    return <Watchlist onSelect={setTicker} />
  }

  return (
    <CompanyDetail
      key={ticker}
      ticker={ticker}
      onBack={() => setTicker(null)}
    />
  )
}
