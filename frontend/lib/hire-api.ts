const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// ── Auth Helpers ──────────────────────────────────────────────────────────────

export function saveToken(token: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem('hire_token', token)
  }
}

export function clearToken(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('hire_token')
  }
}

function getToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('hire_token')
  }
  return null
}

export function isLoggedIn(): boolean {
  if (typeof window !== 'undefined') {
    return !!localStorage.getItem('hire_token')
  }
  return false
}

// ── Internal Request Handler ──────────────────────────────────────────────────

async function hireRequest<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string> | undefined),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  })

  if (res.status === 401) {
    clearToken()
    if (typeof window !== 'undefined') {
      window.location.href = '/hire/login'
    }
    throw new Error('Unauthorized: redirecting to login')
  }

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`API error ${res.status}: ${text}`)
  }

  return res.json() as Promise<T>
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface CandidateCard {
  id: string
  name: string
  email: string
  role: string
  resume_score: number | null
  screen_score: number | null
  updated_at: string | null
}

export interface PipelineCounts {
  applied: number
  pre_screening: number
  pre_screened: number
  test_invited: number
  screened: number
  hr_approved: number
  shortlisted: number
  offer_sent: number
  hired: number
  rejected: number
}

export interface PipelineResponse {
  counts: PipelineCounts
  by_stage: Record<string, CandidateCard[]>
}

export interface ApplicationListItem {
  id: string
  stage: string
  role: string
  name: string
  email: string
  phone: string | null
  resume_score: number | null
  screen_score: number | null
  source: string
  created_at: string | null
  updated_at: string | null
}

export interface ScreenSession {
  id: string
  state: Record<string, unknown>
  started_at: string | null
  completed_at: string | null
}

export interface TestSession {
  id: string
  token: string
  status: string
  aptitude_score: number | null
  english_score: number | null
  overall_score: number | null
  completed_at: string | null
}

export interface ApplicationDetail extends ApplicationListItem {
  location: string | null
  current_ctc: string | number | null
  expected_ctc: string | number | null
  notice_period_days: number | null
  years_experience: number | null
  linkedin_url: string | null
  application_answer: string | null
  rejection_reason: string | null
  screen_session: ScreenSession | null
  test_session: TestSession | null
}

export interface HireConfig {
  hr_resume_score_threshold: number
  hr_screen_score_threshold: number
  hr_test_pass_threshold: number
  hiring_email: string
  admin_notify_email: string
  frontend_url: string
  // Department heads
  hod_bd_email: string
  hod_ops_email: string
  hod_it_email: string
  hod_ai_email: string
  hod_marketing_email: string
  hod_finance_email: string
  hod_hr_email: string
  // Calendly
  calendly_default_link: string
  calendly_bd_link: string
  calendly_ops_link: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

// ── API Functions ─────────────────────────────────────────────────────────────

export async function loginAdmin(
  email: string,
  password: string
): Promise<TokenResponse> {
  return hireRequest<TokenResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export async function getPipeline(): Promise<PipelineResponse> {
  return hireRequest<PipelineResponse>('/hr/dashboard/pipeline')
}

export async function listApplications(
  stage?: string,
  limit = 50,
  offset = 0
): Promise<{ items: ApplicationListItem[]; count: number }> {
  const params = new URLSearchParams()
  if (stage) params.append('stage', stage)
  params.append('limit', limit.toString())
  params.append('offset', offset.toString())

  return hireRequest<{ items: ApplicationListItem[]; count: number }>(
    `/hr/dashboard/applications?${params.toString()}`
  )
}

export async function getApplication(
  id: string
): Promise<ApplicationDetail> {
  return hireRequest<ApplicationDetail>(`/hr/dashboard/applications/${id}`)
}

export async function advanceApplication(
  id: string
): Promise<{ new_stage: string }> {
  return hireRequest<{ new_stage: string }>(
    `/hr/dashboard/applications/${id}/advance`,
    {
      method: 'POST',
    }
  )
}

export async function rejectApplication(
  id: string,
  reason?: string
): Promise<void> {
  await hireRequest<void>(`/hr/dashboard/applications/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  })
}

export async function getHireConfig(): Promise<HireConfig> {
  return hireRequest<HireConfig>('/hr/dashboard/config')
}

export async function updateHireConfig(
  config: Partial<HireConfig>
): Promise<{ saved: Partial<HireConfig> }> {
  return hireRequest<{ saved: Partial<HireConfig> }>(
    '/hr/dashboard/config',
    {
      method: 'PUT',
      body: JSON.stringify(config),
    }
  )
}

export async function generateOffer(
  id: string,
  params: { ctc_lpa: number; joining_date: string; reporting_to: string; location: string }
): Promise<{ message: string; file: string; stage: string }> {
  return hireRequest<{ message: string; file: string; stage: string }>(
    `/hr/dashboard/applications/${id}/generate-offer`,
    {
      method: 'POST',
      body: JSON.stringify(params),
    }
  )
}

export function offerDownloadUrl(id: string): string {
  const token = typeof window !== 'undefined' ? localStorage.getItem('hire_token') ?? '' : ''
  return `${BASE_URL}/hr/dashboard/applications/${id}/offer?token=${encodeURIComponent(token)}`
}

export async function sendOfferEmail(
  id: string
): Promise<{ message: string; to: string }> {
  return hireRequest<{ message: string; to: string }>(
    `/hr/dashboard/applications/${id}/send-offer`,
    { method: 'POST' }
  )
}

export async function scheduleInterview(
  id: string,
  params: { start_iso: string; end_iso: string }
): Promise<{ message: string; meet_link: string; gcal_configured: boolean; candidate_email: string }> {
  return hireRequest(
    `/hr/dashboard/applications/${id}/schedule-interview`,
    { method: 'POST', body: JSON.stringify(params) }
  )
}

export interface AnalyticsFunnelItem {
  stage: string
  count: number
  rate: number
}

export interface AnalyticsRoleRow {
  role: string
  total: number
  avg_resume: number | null
  avg_screen: number | null
}

export interface AnalyticsResponse {
  total: number
  stage_counts: Record<string, number>
  by_role: AnalyticsRoleRow[]
  weekly_intake: { week: string; count: number }[]
  funnel: AnalyticsFunnelItem[]
}

export async function getAnalytics(): Promise<AnalyticsResponse> {
  return hireRequest<AnalyticsResponse>('/hr/dashboard/analytics')
}

export async function hrDecision(
  id: string,
  params: { decision: 'yes' | 'no'; feedback: string; hod_name?: string }
): Promise<{ stage: string; decision: string; hod_notified?: string; calendly_link?: string }> {
  return hireRequest(`/hr/dashboard/applications/${id}/hr-decision`, {
    method: 'POST',
    body: JSON.stringify(params),
  })
}
