import { render, screen } from '@testing-library/react'
import { test, expect } from 'vitest'
import AuditTrail from './AuditTrail'

const ok = { node: 'ingest', success: true, duration_ms: 420, tools_called: 2, llm_calls: 1 }

test('renders a successful pipeline', () => {
  render(<AuditTrail auditSummary={{
    pipeline_id: 'run-42', success: true, total_nodes: 2, total_duration_ms: 4620,
    total_tool_calls: 2, total_llm_calls: 1, total_errors: 0,
    node_breakdown: [ok, { node: 'score', success: true, duration_ms: 4200 }],
    slowest_nodes: [{ node: 'score', duration_ms: 4200 }],
  }} />)
  expect(screen.getByText('2 nodes')).toBeInTheDocument()
  expect(screen.getByText('4.6s')).toBeInTheDocument()
  expect(screen.getByText('OK')).toBeInTheDocument()
  expect(screen.getByText('SLOW')).toBeInTheDocument()
  expect(screen.getByText('2 tools')).toBeInTheDocument()
  expect(screen.getByText('run-42')).toBeInTheDocument()
})

test('shows the empty state with no summary', () => {
  render(<AuditTrail auditSummary={null} />)
  expect(screen.getByText('Run the pipeline to see execution audit.')).toBeInTheDocument()
})

test('marks a failed node and the pipeline as FAIL', () => {
  render(<AuditTrail auditSummary={{
    pipeline_id: 'run-43', success: false, total_errors: 1,
    node_breakdown: [ok, { node: 'gnn_impact', success: false, errors: 1 }],
  }} />)
  expect(screen.getByText('FAIL')).toBeInTheDocument()
  const failed = screen.getByText('gnn_impact').closest('.flex.items-start')
  expect(failed).toHaveTextContent('—')
  expect(failed.querySelector('[style*="border: 2px solid"]').style.border).toMatch(/248, 113, 113|#f87171/)
})
