import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useScenario } from '@/hooks/useScenario'
import {
  approveKnowledgeBundle,
  decideKnowledgeItem,
  fetchKnowledgeBySku,
  fetchKnowledgeList,
} from '@/features/knowledge/services/knowledge.service'
import type { FactDecisionStatus } from '@/types/m02'

export function useKnowledgeList() {
  const { scenario, role } = useScenario()
  return useQuery({
    queryKey: ['knowledge', scenario, role],
    queryFn: () => fetchKnowledgeList({ scenario, role }),
    retry: false,
  })
}

export function useKnowledgeDetail(skuId: string | undefined) {
  const { scenario, role } = useScenario()
  return useQuery({
    queryKey: ['knowledge', skuId, scenario, role],
    queryFn: () => fetchKnowledgeBySku(skuId!, { scenario, role }),
    enabled: Boolean(skuId),
    retry: false,
  })
}

export function useDecideKnowledgeItem(skuId: string) {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (args: { itemId: string; decision: FactDecisionStatus; proposedValue?: string }) =>
      decideKnowledgeItem(
        skuId,
        args.itemId,
        { decision: args.decision, proposedValue: args.proposedValue },
        { scenario, role },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['knowledge'] })
      qc.invalidateQueries({ queryKey: ['products'] })
      qc.invalidateQueries({ queryKey: ['readiness'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useApproveKnowledgeBundle(skuId: string) {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => approveKnowledgeBundle(skuId, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['knowledge'] })
      qc.invalidateQueries({ queryKey: ['products'] })
      qc.invalidateQueries({ queryKey: ['readiness'] })
      qc.invalidateQueries({ queryKey: ['sessions'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
