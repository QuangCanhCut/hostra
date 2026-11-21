import { apiRequest, type RequestContext } from '@/services/api-client'
import type { StoryArcItem, StoryPlanDetail } from '@/types/m02'

export function fetchStoryPlan(
  sessionId: string,
  context: RequestContext,
): Promise<StoryPlanDetail> {
  return apiRequest<StoryPlanDetail>(`/api/mock/v1/sessions/${sessionId}/story`, context)
}

export function updateStoryArcs(
  sessionId: string,
  arcs: StoryArcItem[],
  summary: string,
  context: RequestContext,
): Promise<StoryPlanDetail> {
  return apiRequest<StoryPlanDetail>(`/api/mock/v1/sessions/${sessionId}/story`, context, {
    method: 'PUT',
    body: JSON.stringify({ arcs, summary }),
  })
}

export function requestStoryAiSuggestion(
  sessionId: string,
  prompt: string,
  context: RequestContext,
): Promise<StoryPlanDetail> {
  return apiRequest<StoryPlanDetail>(
    `/api/mock/v1/sessions/${sessionId}/story/ai-suggest`,
    context,
    {
      method: 'POST',
      body: JSON.stringify({ prompt }),
    },
  )
}

export function resolveStoryAiProposal(
  sessionId: string,
  action: 'APPLY' | 'REJECT',
  context: RequestContext,
): Promise<StoryPlanDetail> {
  return apiRequest<StoryPlanDetail>(
    `/api/mock/v1/sessions/${sessionId}/story/ai-apply`,
    context,
    {
      method: 'POST',
      body: JSON.stringify({ action }),
    },
  )
}

export function approveStoryRevision(
  sessionId: string,
  context: RequestContext,
): Promise<StoryPlanDetail> {
  return apiRequest<StoryPlanDetail>(
    `/api/mock/v1/sessions/${sessionId}/story/approve`,
    context,
    { method: 'POST' },
  )
}
