import { apiRequest, type RequestContext } from '@/services/api-client'
import type {
  PresenterDetail,
  PresenterDraftPayload,
  RightsConsentRecord,
} from '@/types/m02'

export function fetchPresenters(
  context: RequestContext,
): Promise<{ items: PresenterDetail[] }> {
  return apiRequest<{ items: PresenterDetail[] }>('/api/mock/v1/presenters', context)
}

export function fetchPresenterById(
  id: string,
  context: RequestContext,
): Promise<PresenterDetail> {
  return apiRequest<PresenterDetail>(`/api/mock/v1/presenters/${id}`, context)
}

export function createPresenterDraft(
  payload: PresenterDraftPayload,
  context: RequestContext,
): Promise<PresenterDetail> {
  return apiRequest<PresenterDetail>('/api/mock/v1/presenters', context, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function triggerPresenterGeneration(
  id: string,
  context: RequestContext,
): Promise<PresenterDetail> {
  return apiRequest<PresenterDetail>(`/api/mock/v1/presenters/${id}/generate`, context, {
    method: 'POST',
  })
}

export function retryFailedPresenterClip(
  id: string,
  context: RequestContext,
): Promise<PresenterDetail> {
  return apiRequest<PresenterDetail>(`/api/mock/v1/presenters/${id}/retry-clip`, context, {
    method: 'POST',
  })
}

export function approvePresenterPack(
  id: string,
  packId: string,
  decision: 'APPROVE' | 'REWORK',
  context: RequestContext,
): Promise<PresenterDetail> {
  return apiRequest<PresenterDetail>(`/api/mock/v1/presenters/${id}/approve`, context, {
    method: 'POST',
    body: JSON.stringify({ packId, decision }),
  })
}

export function fetchRightsRequest(
  requestId: string,
  context: RequestContext,
): Promise<{ presenterName: string; consent: RightsConsentRecord }> {
  return apiRequest<{ presenterName: string; consent: RightsConsentRecord }>(
    `/api/mock/v1/rights/${requestId}`,
    context,
  )
}

export function submitRightsDecision(
  requestId: string,
  action: 'ACCEPT' | 'DECLINE' | 'REVOKE',
  context: RequestContext,
): Promise<{ presenterName: string; consent: RightsConsentRecord }> {
  return apiRequest<{ presenterName: string; consent: RightsConsentRecord }>(
    `/api/mock/v1/rights/${requestId}/decision`,
    context,
    {
      method: 'POST',
      body: JSON.stringify({ action }),
    },
  )
}
