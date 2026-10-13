import { render, screen } from '@testing-library/react'
import { test, expect } from 'vitest'
import SectorHeatmap from './SectorHeatmap'

const cell = name => screen.getByText(name).parentElement

test('averages scores per sector', () => {
  render(<SectorHeatmap alphaScores={{ XOM: 2, CVX: 4, JNJ: -3 }} />)
  expect(cell('Energy')).toHaveTextContent('+3.0')
  expect(cell('Healthcare')).toHaveTextContent('-3.0')
})

test('empty scores render every sector as "no data", not a neutral 0', () => {
  render(<SectorHeatmap alphaScores={{}} />)
  expect(screen.getAllByText('no data')).toHaveLength(8)
  expect(screen.queryByText('0.0')).not.toBeInTheDocument()
})

test('a failed source (non-numeric scores) is excluded rather than averaged as 0', () => {
  render(<SectorHeatmap alphaScores={{ XOM: null, CVX: 'error', COP: 6, AAPL: undefined }} />)
  expect(cell('Energy')).toHaveTextContent('+6.0')
  expect(cell('Technology')).toHaveTextContent('no data')
})
