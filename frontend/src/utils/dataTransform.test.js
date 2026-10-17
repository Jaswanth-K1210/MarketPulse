import { test, expect } from 'vitest'
import { transformStats } from './dataTransform'

test('impact score is derived from average_impact', () => {
  expect(transformStats({ average_impact: -0.42 }).marketImpactScore).toBe('4.2')
})

test('a real average of 0 is a score of 0, not missing', () => {
  expect(transformStats({ average_impact: 0 }).marketImpactScore).toBe('0.0')
})

test('no average_impact gives no score instead of an invented 7.2', () => {
  expect(transformStats({}).marketImpactScore).toBeNull()
  expect(transformStats({ average_impact: null }).marketImpactScore).toBeNull()
})

import { parseTimestamp, alertCountsLast7Days, transformAlert } from './dataTransform'

test('parseTimestamp reads naive backend timestamps as UTC', () => {
  expect(parseTimestamp('2026-10-06 22:42:03.394186').toISOString()).toBe('2026-10-06T22:42:03.394Z')
  expect(parseTimestamp('2026-10-06T22:42:03+02:00').toISOString()).toBe('2026-10-06T20:42:03.000Z')
})

test('parseTimestamp rejects missing and non-date values', () => {
  for (const v of [null, undefined, '', '2 hours ago', 'not-a-date']) expect(parseTimestamp(v)).toBeNull()
})

test('transformAlert keeps the real timestamp, not a relative string', () => {
  const a = transformAlert({ created_at: '2026-10-06 22:42:03.394186' })
  expect(parseTimestamp(a.timestamp)).not.toBeNull()
})

const now = new Date(2026, 9, 15, 12, 0)          // Thu 15 Oct 2026, local noon
const daysAgo = (n, h = 10) => new Date(2026, 9, 15 - n, h).toISOString()

test('counts alerts per day for the last 7 days, oldest first, ending today', () => {
  const alerts = [
    { created_at: daysAgo(0) }, { created_at: daysAgo(0, 1) },
    { created_at: daysAgo(2) },
    { created_at: daysAgo(6) },
    { created_at: daysAgo(7) },                     // outside the window
    { created_at: new Date(2026, 9, 16, 9).toISOString() }, // future, ignored
    { timestamp: 'not-a-date' },
  ]
  const days = alertCountsLast7Days(alerts, now)
  expect(days.map(d => d.count)).toEqual([1, 0, 0, 0, 1, 0, 2])
  expect(days.map(d => d.label)).toEqual(['Fri', 'Sat', 'Sun', 'Mon', 'Tue', 'Wed', 'Thu'])
})

test('alerts in the window can all be zero without inventing a trend', () => {
  expect(alertCountsLast7Days([{ created_at: daysAgo(30) }], now).map(d => d.count)).toEqual([0, 0, 0, 0, 0, 0, 0])
})

test('returns null when no alert has a usable timestamp', () => {
  expect(alertCountsLast7Days([], now)).toBeNull()
  expect(alertCountsLast7Days([{ timestamp: '2 hours ago' }, {}], now)).toBeNull()
})
