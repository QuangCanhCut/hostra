import { useQuery } from '@tanstack/react-query'
import { useScenario } from '@/hooks/useScenario'
import { fetchSessionReport } from '../services/reports.service'

export function useSessionReport(sessionId: string | undefined) {
  const { scenario, role } = useScenario()
  return useQuery({
    queryKey: ['session-report', scenario, role, sessionId],
    queryFn: () => fetchSessionReport(sessionId!, { scenario, role }),
    enabled: Boolean(sessionId),
    retry: false,
  })
}
