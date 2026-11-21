import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useScenario } from '@/hooks/useScenario'
import {
  approveStoryRevision,
  fetchStoryPlan,
  requestStoryAiSuggestion,
  resolveStoryAiProposal,
  updateStoryArcs,
} from '@/features/story-planner/services/story.service'
import type { StoryArcItem } from '@/types/m02'

export function useStoryPlan(sessionId: string | undefined) {
  const { scenario, role } = useScenario()
  return useQuery({
    queryKey: ['story', sessionId, scenario, role],
    queryFn: () => fetchStoryPlan(sessionId!, { scenario, role }),
    enabled: Boolean(sessionId),
    retry: false,
  })
}

export function useUpdateStoryArcs(sessionId: string) {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (args: { arcs: StoryArcItem[]; summary: string }) =>
      updateStoryArcs(sessionId, args.arcs, args.summary, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['story', sessionId] })
      qc.invalidateQueries({ queryKey: ['readiness', sessionId] })
      qc.invalidateQueries({ queryKey: ['sessions'] })
    },
  })
}

export function useRequestStoryAi(sessionId: string) {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (prompt: string) =>
      requestStoryAiSuggestion(sessionId, prompt, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['story', sessionId] })
    },
  })
}

export function useResolveStoryAi(sessionId: string) {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (action: 'APPLY' | 'REJECT') =>
      resolveStoryAiProposal(sessionId, action, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['story', sessionId] })
      qc.invalidateQueries({ queryKey: ['readiness', sessionId] })
      qc.invalidateQueries({ queryKey: ['sessions'] })
    },
  })
}

export function useApproveStory(sessionId: string) {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => approveStoryRevision(sessionId, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['story', sessionId] })
      qc.invalidateQueries({ queryKey: ['readiness', sessionId] })
      qc.invalidateQueries({ queryKey: ['sessions'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
