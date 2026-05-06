const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`API error ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

// ── Types ────────────────────────────────────────────────────────────────────

export interface Citation {
  entity_name: string
  entity_type: string
  source: string
}

export interface QueryResult {
  answer: string
  citations: Citation[]
  confidence: number
  intent: string
  policy_violations: { rule: string; severity: string }[]
  context_entities_used: string[]
}

export interface FeedbackPayload {
  question: string
  claude_answer: string
  correct_answer: string
  corrected_by: string
  feedback_type: string
}

export interface ICP {
  industries: string[]
  seat_range: { min: number; max: number }
  geographies: string[]
  confidence: number
  [key: string]: unknown
}

export interface Decision {
  id: string
  decision_type: string
  actor: string
  human_action: string
  human_reasoning?: string
  primary_entity_id?: string
  context_snapshot?: Record<string, unknown>
  outcome?: string
  timestamp: string
  [key: string]: unknown
}

export interface DecisionPayload {
  decision_type: string
  actor: string
  human_action: string
  human_reasoning?: string
  primary_entity_id?: string
  context_snapshot?: Record<string, unknown>
}

export interface Entity {
  id: string
  name: string
  entity_type: string
  [key: string]: unknown
}

export interface HealthStatus {
  status: string
  version?: string
  [key: string]: unknown
}

export interface QualityIssue {
  severity: string
  entity_name?: string
  message: string
  [key: string]: unknown
}

export interface QualityReport {
  score: number
  issues: QualityIssue[]
  [key: string]: unknown
}

export interface Rule {
  id: string
  name: string
  reasoning?: string
  condition: Record<string, unknown>
  action: Record<string, unknown>
  created_by: string
  fire_count: number
  active: boolean
  [key: string]: unknown
}

export interface RulePayload {
  name: string
  reasoning?: string
  condition: Record<string, unknown>
  action: Record<string, unknown>
  created_by: string
}

export interface EvalCase {
  id: string
  question: string
  expected_themes: string[]
  min_expected_score: number
  created_by: string
  [key: string]: unknown
}

export interface EvalCasePayload {
  question: string
  expected_themes: string[]
  min_expected_score: number
  created_by: string
}

export interface EvalRun {
  id: string
  triggered_by: string
  started_at: string
  avg_score: number
  cases_passed: number
  cases_run: number
  [key: string]: unknown
}

export interface EvalResult {
  case_id: string
  question: string
  score: number
  passed: boolean
  [key: string]: unknown
}

export interface OversightSummary {
  total_decisions: number
  total_entities: number
  last_eval_score?: number
  quality_score?: number
  [key: string]: unknown
}

export interface Policy {
  id: string
  name: string
  severity: 'block' | 'warn' | 'flag'
  fire_count: number
  description: string
  [key: string]: unknown
}

// ── API Functions ─────────────────────────────────────────────────────────────

export async function queryContext(
  question: string,
  entityId?: string
): Promise<QueryResult> {
  return request<QueryResult>('/context/query', {
    method: 'POST',
    body: JSON.stringify({ question, entity_id: entityId }),
  })
}

export async function submitFeedback(
  question: string,
  claudeAnswer: string,
  correctAnswer: string,
  correctedBy: string,
  feedbackType: string
): Promise<unknown> {
  return request('/context/feedback', {
    method: 'POST',
    body: JSON.stringify({
      question,
      claude_answer: claudeAnswer,
      correct_answer: correctAnswer,
      corrected_by: correctedBy,
      feedback_type: feedbackType,
    }),
  })
}

export async function getICP(): Promise<ICP> {
  return request<ICP>('/context/icp')
}

export async function listDecisions(limit = 20): Promise<Decision[]> {
  return request<Decision[]>(`/decisions?limit=${limit}`)
}

export async function createDecision(body: DecisionPayload): Promise<Decision> {
  return request<Decision>('/decisions', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function recordOutcome(
  id: string,
  outcome: string,
  feedback_signal: string
): Promise<Decision> {
  return request<Decision>(`/decisions/${id}/outcome`, {
    method: 'PATCH',
    body: JSON.stringify({ outcome, feedback_signal }),
  })
}

export async function listEntities(limit = 50): Promise<Entity[]> {
  return request<Entity[]>(`/entities?limit=${limit}`)
}

export async function getHealth(): Promise<HealthStatus> {
  return request<HealthStatus>('/health')
}

export async function runQualityCheck(): Promise<QualityReport> {
  return request<QualityReport>('/context/quality')
}

export async function listRules(activeOnly?: boolean): Promise<Rule[]> {
  const qs = activeOnly !== undefined ? `?active_only=${activeOnly}` : ''
  return request<Rule[]>(`/rules${qs}`)
}

export async function createRule(body: RulePayload): Promise<Rule> {
  return request<Rule>('/rules', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function listEvalCases(): Promise<EvalCase[]> {
  return request<EvalCase[]>('/evals/cases')
}

export async function createEvalCase(body: EvalCasePayload): Promise<EvalCase> {
  return request<EvalCase>('/evals/cases', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function triggerEvalRun(triggeredBy: string): Promise<EvalRun> {
  return request<EvalRun>('/evals/run', {
    method: 'POST',
    body: JSON.stringify({ triggered_by: triggeredBy }),
  })
}

export async function listEvalRuns(limit = 10): Promise<EvalRun[]> {
  return request<EvalRun[]>(`/evals/runs?limit=${limit}`)
}

export async function getEvalRunResults(runId: string): Promise<EvalResult[]> {
  return request<EvalResult[]>(`/evals/runs/${runId}/results`)
}

export async function getOversightSummary(): Promise<OversightSummary> {
  return request<OversightSummary>('/oversight/summary')
}

export async function listPolicies(): Promise<Policy[]> {
  return request<Policy[]>('/oversight/policies')
}

export async function runLearn(): Promise<unknown> {
  return request('/context/learn', { method: 'POST' })
}

export async function refreshICP(): Promise<ICP> {
  return request<ICP>('/context/icp/refresh', { method: 'POST' })
}
