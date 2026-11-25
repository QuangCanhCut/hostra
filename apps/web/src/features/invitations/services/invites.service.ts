import { apiRequest, type RequestContext } from '@/services/api-client'
import type { ViewerInviteRecord } from '@/types/m03'

export function fetchInvites(
  sessionId: string | undefined,
  context: RequestContext,
): Promise<{ items: ViewerInviteRecord[] }> {
  const qs = sessionId ? `?sessionId=${encodeURIComponent(sessionId)}` : ''
  return apiRequest<{ items: ViewerInviteRecord[] }>(`/api/mock/v1/invites${qs}`, context)
}

export function createInvite(
  payload: {
    sessionId: string
    label: string
    usageCap: number
    expiresAt: string
  },
  context: RequestContext,
): Promise<ViewerInviteRecord> {
  return apiRequest<ViewerInviteRecord>('/api/mock/v1/invites', context, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function revokeInvite(
  inviteId: string,
  context: RequestContext,
): Promise<{ invite: ViewerInviteRecord; ejectedCount: number }> {
  return apiRequest<{ invite: ViewerInviteRecord; ejectedCount: number }>(
    `/api/mock/v1/invites/${inviteId}/revoke`,
    context,
    { method: 'POST' },
  )
}
