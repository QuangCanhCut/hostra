import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useScenario } from '@/hooks/useScenario'
import {
  approvePresenterPack,
  createPresenterDraft,
  fetchPresenterById,
  fetchPresenters,
  fetchRightsRequest,
  retryFailedPresenterClip,
  submitRightsDecision,
  triggerPresenterGeneration,
} from '@/features/presenter/services/presenter.service'
import type { PresenterDraftPayload } from '@/types/m02'

export function usePresenters() {
  const { scenario, role } = useScenario()
  return useQuery({
    queryKey: ['presenters', scenario, role],
    queryFn: () => fetchPresenters({ scenario, role }),
    retry: false,
  })
}

export function usePresenterDetail(id: string | undefined) {
  const { scenario, role } = useScenario()
  return useQuery({
    queryKey: ['presenters', id, scenario, role],
    queryFn: () => fetchPresenterById(id!, { scenario, role }),
    enabled: Boolean(id),
    retry: false,
  })
}

export function useCreatePresenter() {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: PresenterDraftPayload) =>
      createPresenterDraft(payload, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['presenters'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useGeneratePresenter(id: string) {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => triggerPresenterGeneration(id, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['presenters'] })
      qc.invalidateQueries({ queryKey: ['readiness'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useRetryPresenterClip(id: string) {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => retryFailedPresenterClip(id, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['presenters'] })
      qc.invalidateQueries({ queryKey: ['readiness'] })
    },
  })
}

export function useApprovePresenter(id: string) {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (args: { packId: string; decision: 'APPROVE' | 'REWORK' }) =>
      approvePresenterPack(id, args.packId, args.decision, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['presenters'] })
      qc.invalidateQueries({ queryKey: ['readiness'] })
      qc.invalidateQueries({ queryKey: ['sessions'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useRightsConsent(requestId: string | undefined) {
  const { scenario, role } = useScenario()
  return useQuery({
    queryKey: ['rights', requestId, scenario, role],
    queryFn: () => fetchRightsRequest(requestId!, { scenario, role }),
    enabled: Boolean(requestId),
    retry: false,
  })
}

export function useSubmitRightsDecision(requestId: string) {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (action: 'ACCEPT' | 'DECLINE' | 'REVOKE') =>
      submitRightsDecision(requestId, action, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['rights'] })
      qc.invalidateQueries({ queryKey: ['presenters'] })
      qc.invalidateQueries({ queryKey: ['readiness'] })
      qc.invalidateQueries({ queryKey: ['sessions'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
