import { render, screen, fireEvent } from '@testing-library/react'
import { vi, test, expect } from 'vitest'
import AlertCard from './AlertCard'

test('renders a normal alert and opens the explanation on click', () => {
  const alert = { severity: 'HIGH', ticker: 'NVDA', description: 'Export curbs widened', impact_percent: -3.456, timestamp: new Date().toISOString() }
  const onExplain = vi.fn()
  render(<AlertCard alert={alert} onExplain={onExplain} />)
  expect(screen.getByText('HIGH')).toBeInTheDocument()
  expect(screen.getByText('NVDA — Export curbs widened')).toBeInTheDocument()
  expect(screen.getByText('-3.46%')).toBeInTheDocument()
  expect(screen.getByText(/s ago$/)).toBeInTheDocument()
  fireEvent.click(screen.getByText('HIGH'))
  expect(onExplain).toHaveBeenCalledWith(alert)
})

test('falls back to placeholders for an empty alert', () => {
  render(<AlertCard alert={{}} onExplain={() => {}} />)
  expect(screen.getByText('LOW')).toBeInTheDocument()
  expect(screen.getByText('Market event')).toBeInTheDocument()
  expect(screen.getByText('—')).toBeInTheDocument()
})

test('a failed upstream node (null impact, no timestamp) shows no fabricated numbers', () => {
  const { container } = render(<AlertCard alert={{ severity: 'MEDIUM', event: 'Feed down', impact_percent: null, timestamp: 'not-a-date' }} onExplain={() => {}} />)
  expect(screen.getByText('—')).toBeInTheDocument()
  expect(container.textContent).not.toMatch(/0\.00%|NaN|ago/)
})
