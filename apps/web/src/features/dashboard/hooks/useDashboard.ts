import { useQuery } from '@tanstack/react-query'
import { useScenario } from '@/hooks/useScenario'
import { fetchDashboardSnapshot } from '@/features/dashboard/services/dashboard.service'

export function useDashboard() {
  const { scenario, role } = useScenario()

  return useQuery({
    queryKey: ['dashboard', 'snapshot', scenario, role],
    queryFn: () => fetchDashboardSnapshot({ scenario, role }),
    retry: false,
  })
}
