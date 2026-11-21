import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useScenario } from '@/hooks/useScenario'
import {
  fetchMembers,
  inviteOperator,
  updateMemberAssignments,
} from '@/features/members/services/members.service'

export function useMembers() {
  const { scenario, role } = useScenario()
  return useQuery({
    queryKey: ['members', scenario, role],
    queryFn: () => fetchMembers({ scenario, role }),
    retry: false,
  })
}

export function useInviteOperator() {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (email: string) => inviteOperator(email, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['members'] })
    },
  })
}

export function useUpdateAssignments() {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (args: {
      memberId: string
      assignedSessionIds: string[]
      expectedRevision: number
    }) =>
      updateMemberAssignments(
        args.memberId,
        args.assignedSessionIds,
        args.expectedRevision,
        { scenario, role },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['members'] })
      qc.invalidateQueries({ queryKey: ['sessions'] })
      qc.invalidateQueries({ queryKey: ['control-room'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
