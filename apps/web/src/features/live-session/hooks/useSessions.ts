import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useScenario } from '@/hooks/useScenario'
import {
  createSession,
  fetchOnboardingDraft,
  fetchReadiness,
  fetchSessionById,
  fetchSessions,
  saveOnboardingDraft,
  sendStartSessionCommand,
  updateSession,
} from '@/features/live-session/services/sessions.service'
import type { OnboardingDraft, SessionDetail } from '@/types/m02'

export function useSessions() {
  const { scenario, role } = useScenario()
  return useQuery({
    queryKey: ['sessions', scenario, role],
    queryFn: () => fetchSessions({ scenario, role }),
    retry: false,
  })
}

export function useSessionDetail(id: string | undefined) {
  const { scenario, role } = useScenario()
  return useQuery({
    queryKey: ['sessions', id, scenario, role],
    queryFn: () => fetchSessionById(id!, { scenario, role }),
    enabled: Boolean(id),
    retry: false,
  })
}

export function useCreateSession() {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: {
      title: string
      presenterId: string
      selectedSkuIds: string[]
      goal: string
      theme: string
      estimatedMinutes: number
      prioritySkuId: string | null
      mandatoryMessages: string
    }) => createSession(payload, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sessions'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useUpdateSession(id: string) {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Partial<SessionDetail>) =>
      updateSession(id, payload, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sessions'] })
      qc.invalidateQueries({ queryKey: ['story', id] })
      qc.invalidateQueries({ queryKey: ['readiness', id] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useReadiness(sessionId: string | undefined) {
  const { scenario, role } = useScenario()
  return useQuery({
    queryKey: ['readiness', sessionId, scenario, role],
    queryFn: () => fetchReadiness(sessionId!, { scenario, role }),
    enabled: Boolean(sessionId),
    retry: false,
  })
}

export function useStartSession(sessionId: string) {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (phase: 'REQUEST' | 'CONFIRM_MEDIA') =>
      sendStartSessionCommand(sessionId, phase, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['readiness', sessionId] })
      qc.invalidateQueries({ queryKey: ['sessions'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useOnboardingDraft() {
  const { scenario, role } = useScenario()
  return useQuery({
    queryKey: ['onboarding', scenario, role],
    queryFn: () => fetchOnboardingDraft({ scenario, role }),
    retry: false,
  })
}

export function useSaveOnboardingDraft() {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Partial<OnboardingDraft>) =>
      saveOnboardingDraft(payload, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['onboarding'] })
    },
  })
}
