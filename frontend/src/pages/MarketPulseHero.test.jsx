import { render, screen } from '@testing-library/react'
import { test, expect, vi, afterEach } from 'vitest'
import { MarketPulseHero } from './Dashboard'

const impactCell = () => screen.getByText('IMPACT SCORE').previousElementSibling

test('shows the impact score when stats have one', () => {
  render(<MarketPulseHero alerts={[]} stats={{ marketImpactScore: '4.2' }} />)
  expect(impactCell()).toHaveTextContent('4.2')
})

test('shows a dash, not 7.2, when there is no score', () => {
  const { container } = render(<MarketPulseHero alerts={[]} stats={{ marketImpactScore: null }} />)
  expect(impactCell()).toHaveTextContent('—')
  expect(container.textContent).not.toContain('7.2')
})

test('shows a dash when stats have not loaded', () => {
  render(<MarketPulseHero alerts={[]} stats={undefined} />)
  expect(impactCell()).toHaveTextContent('—')
})

afterEach(() => vi.useRealTimers())

test('plots real per-day counts: alerts only today means six flat zero days', () => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(2026, 9, 15, 12, 0))
  const today = new Date(2026, 9, 15, 9).toISOString()
  const { container } = render(<MarketPulseHero alerts={[{ created_at: today }, { created_at: today }]} stats={{}} />)
  expect(screen.getByText('ALERT TREND')).toBeInTheDocument()
  const ys = [...container.querySelectorAll('svg circle')].map(c => c.getAttribute('cy'))
  expect(ys).toHaveLength(7)
  expect(new Set(ys.slice(0, 6)).size).toBe(1)     // the old chart drew 2,5,3,8,4,6 here
  expect(Number(ys[6])).toBeLessThan(Number(ys[0]))
  expect(screen.getByText('Thu')).toBeInTheDocument()
})

test('hides the chart when alerts have no timestamps', () => {
  const { container } = render(<MarketPulseHero alerts={[{ severity: 'HIGH' }, { timestamp: '2 hours ago' }]} stats={{}} />)
  expect(screen.queryByText('ALERT TREND')).not.toBeInTheDocument()
  expect(container.querySelector('svg circle')).toBeNull()
  expect(screen.getByText('HIGH/CRIT')).toBeInTheDocument()
})
