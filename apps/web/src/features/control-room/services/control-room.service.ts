import { apiRequest, type RequestContext } from '@/services/api-client'
import type {
  ControlRoomSnapshot,
  RuntimeCommandRecord,
  RuntimeCommandType,
} from '@/types/m03'

export function fetchControlRoom(
  sessionId: string,
  context: RequestContext,
): Promise<ControlRoomSnapshot> {
  return apiRequest<ControlRoomSnapshot>(
    `/api/mock/v1/sessions/${sessionId}/control`,
    context,
  )
}

export function sendControlCommand(
  sessionId: string,
  payload: {
    type: RuntimeCommandType
    expectedRevision: number
    targetSkuId?: string
    commentId?: string
    simulatePhase?: 'ACCEPT_ONLY' | 'APPLY'
  },
  context: RequestContext,
): Promise<{ command: RuntimeCommandRecord; snapshot: ControlRoomSnapshot }> {
  return apiRequest<{ command: RuntimeCommandRecord; snapshot: ControlRoomSnapshot }>(
    `/api/mock/v1/sessions/${sessionId}/control/command`,
    context,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  )
}

export function advanceSpeechPhase(
  sessionId: string,
  context: RequestContext,
): Promise<ControlRoomSnapshot> {
  return apiRequest<ControlRoomSnapshot>(
    `/api/mock/v1/sessions/${sessionId}/control/advance-speech`,
    context,
    { method: 'POST' },
  )
}

export function simulateControlEvent(
  sessionId: string,
  kind: 'TOGGLE_DEGRADED' | 'TOGGLE_STALE' | 'SIMULATE_CONFLICT',
  context: RequestContext,
): Promise<ControlRoomSnapshot> {
  return apiRequest<ControlRoomSnapshot>(
    `/api/mock/v1/sessions/${sessionId}/control/simulate-event`,
    context,
    {
      method: 'POST',
      body: JSON.stringify({ kind }),
    },
  )
}
