import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useScenario } from '@/hooks/useScenario'
import {
  admitViewer,
  fetchViewerRoom,
  submitViewerComment,
} from '@/features/viewer/services/viewer.service'

export function useViewerRoom(
  sessionId: string,
  inviteToken: string | null,
  guestSessionId: string | null,
) {
  const { scenario, role } = useScenario()
  return useQuery({
    queryKey: ['viewer', sessionId, inviteToken, guestSessionId, scenario],
    queryFn: () => fetchViewerRoom(sessionId, inviteToken, guestSessionId, { scenario, role }),
    retry: false,
  })
}

export function useAdmitViewer(sessionId: string) {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: {
      inviteToken: string | null
      nickname: string
      existingGuestSessionId?: string | null
    }) => admitViewer(sessionId, payload, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['viewer', sessionId] })
      qc.invalidateQueries({ queryKey: ['invites'] })
      qc.invalidateQueries({ queryKey: ['reports'] })
    },
  })
}

export function useSubmitViewerComment(sessionId: string) {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: {
      guestSessionId: string
      nickname: string
      body: string
      clientSubmissionId: string
    }) => submitViewerComment(sessionId, payload, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['viewer', sessionId] })
      qc.invalidateQueries({ queryKey: ['control-room', sessionId] })
      qc.invalidateQueries({ queryKey: ['reports'] })
    },
  })
}
