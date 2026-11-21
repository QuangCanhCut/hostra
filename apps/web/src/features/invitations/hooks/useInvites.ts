import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useScenario } from '@/hooks/useScenario'
import {
  createInvite,
  fetchInvites,
  revokeInvite,
} from '@/features/invitations/services/invites.service'

export function useInvites(sessionId?: string) {
  const { scenario, role } = useScenario()
  return useQuery({
    queryKey: ['invites', sessionId ?? 'all', scenario, role],
    queryFn: () => fetchInvites(sessionId, { scenario, role }),
    retry: false,
  })
}

export function useCreateInvite() {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: {
      sessionId: string
      label: string
      usageCap: number
      expiresAt: string
    }) => createInvite(payload, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invites'] })
      qc.invalidateQueries({ queryKey: ['control-room'] })
      qc.invalidateQueries({ queryKey: ['members'] })
    },
  })
}

export function useRevokeInvite() {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (inviteId: string) => revokeInvite(inviteId, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invites'] })
      qc.invalidateQueries({ queryKey: ['viewer'] })
      qc.invalidateQueries({ queryKey: ['members'] })
    },
  })
}
