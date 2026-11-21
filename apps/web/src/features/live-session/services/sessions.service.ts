import { apiRequest, type RequestContext } from '@/services/api-client'
import type {
  OnboardingDraft,
  ReadinessSnapshot,
  SessionDetail,
  StartCommandResult,
} from '@/types/m02'

export function fetchSessions(
  context: RequestContext,
): Promise<{ items: SessionDetail[] }> {
  return apiRequest<{ items: SessionDetail[] }>('/api/mock/v1/sessions', context)
}

export function fetchSessionById(
  id: string,
  context: RequestContext,
): Promise<SessionDetail> {
  return apiRequest<SessionDetail>(`/api/mock/v1/sessions/${id}`, context)
}

export function createSession(
  payload: {
    title: string
    presenterId: string
    selectedSkuIds: string[]
    goal: string
    theme: string
    estimatedMinutes: number
    prioritySkuId: string | null
    mandatoryMessages: string
  },
  context: RequestContext,
): Promise<SessionDetail> {
  return apiRequest<SessionDetail>('/api/mock/v1/sessions', context, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateSession(
  id: string,
  payload: Partial<SessionDetail>,
  context: RequestContext,
): Promise<SessionDetail> {
  return apiRequest<SessionDetail>(`/api/mock/v1/sessions/${id}`, context, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function fetchReadiness(
  sessionId: string,
  context: RequestContext,
): Promise<ReadinessSnapshot> {
  return apiRequest<ReadinessSnapshot>(
    `/api/mock/v1/sessions/${sessionId}/readiness`,
    context,
  )
}

export function sendStartSessionCommand(
  sessionId: string,
  phase: 'REQUEST' | 'CONFIRM_MEDIA',
  context: RequestContext,
): Promise<StartCommandResult> {
  return apiRequest<StartCommandResult>(
    `/api/mock/v1/sessions/${sessionId}/start`,
    context,
    {
      method: 'POST',
      body: JSON.stringify({ phase }),
    },
  )
}

export function fetchOnboardingDraft(
  context: RequestContext,
): Promise<OnboardingDraft> {
  return apiRequest<OnboardingDraft>('/api/mock/v1/onboarding', context)
}

export function saveOnboardingDraft(
  payload: Partial<OnboardingDraft>,
  context: RequestContext,
): Promise<OnboardingDraft> {
  return apiRequest<OnboardingDraft>('/api/mock/v1/onboarding', context, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}
