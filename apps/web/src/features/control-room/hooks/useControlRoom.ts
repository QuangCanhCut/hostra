import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useScenario } from '@/hooks/useScenario'
import {
  advanceSpeechPhase,
  fetchControlRoom,
  sendControlCommand,
  simulateControlEvent,
} from '@/features/control-room/services/control-room.service'
import type { RuntimeCommandType } from '@/types/m03'

export function useControlRoom(sessionId: string | undefined) {
  const { scenario, role } = useScenario()
  return useQuery({
    queryKey: ['control-room', sessionId, scenario, role],
    queryFn: () => fetchControlRoom(sessionId!, { scenario, role }),
    enabled: Boolean(sessionId),
    retry: false,
  })
}

export function useControlCommand(sessionId: string) {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: {
      type: RuntimeCommandType
      expectedRevision: number
      targetSkuId?: string
      commentId?: string
      simulatePhase?: 'ACCEPT_ONLY' | 'APPLY'
    }) => sendControlCommand(sessionId, payload, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['control-room', sessionId] })
      qc.invalidateQueries({ queryKey: ['sessions'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
      qc.invalidateQueries({ queryKey: ['viewer'] })
      qc.invalidateQueries({ queryKey: ['reports'] })
    },
  })
}

export function useAdvanceSpeech(sessionId: string) {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => advanceSpeechPhase(sessionId, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['control-room', sessionId] })
      qc.invalidateQueries({ queryKey: ['reports'] })
    },
  })
}

export function useSimulateControlEvent(sessionId: string) {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (kind: 'TOGGLE_DEGRADED' | 'TOGGLE_STALE' | 'SIMULATE_CONFLICT') =>
      simulateControlEvent(sessionId, kind, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['control-room', sessionId] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
      qc.invalidateQueries({ queryKey: ['sessions'] })
    },
  })
}
