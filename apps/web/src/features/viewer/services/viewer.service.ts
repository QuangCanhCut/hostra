import { apiRequest, type RequestContext } from '@/services/api-client'
import type { ViewerRoomSnapshot } from '@/types/m03'

export function fetchViewerRoom(
  sessionId: string,
  inviteToken: string | null,
  guestSessionId: string | null,
  context: RequestContext,
): Promise<ViewerRoomSnapshot> {
  const params = new URLSearchParams()
  if (inviteToken) params.set('invite', inviteToken)
  if (guestSessionId) params.set('guestSessionId', guestSessionId)
  const qs = params.toString() ? `?${params.toString()}` : ''
  return apiRequest<ViewerRoomSnapshot>(`/api/mock/v1/viewer/${sessionId}${qs}`, context)
}

export function admitViewer(
  sessionId: string,
  payload: {
    inviteToken: string | null
    nickname: string
    existingGuestSessionId?: string | null
  },
  context: RequestContext,
): Promise<ViewerRoomSnapshot> {
  return apiRequest<ViewerRoomSnapshot>(`/api/mock/v1/viewer/${sessionId}/admit`, context, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function submitViewerComment(
  sessionId: string,
  payload: {
    guestSessionId: string
    nickname: string
    body: string
    clientSubmissionId: string
  },
  context: RequestContext,
): Promise<{ receiptStatus: 'RECEIVED'; commentId: string }> {
  return apiRequest<{ receiptStatus: 'RECEIVED'; commentId: string }>(
    `/api/mock/v1/viewer/${sessionId}/comments`,
    context,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  )
}
