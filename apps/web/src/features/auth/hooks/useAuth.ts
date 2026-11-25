import { useQuery } from '@tanstack/react-query'
import { useScenario } from '@/hooks/useScenario'
import { fetchAuthSnapshot } from '@/services/auth.service'

export function useAuth() {
  const { scenario, role } = useScenario()

  return useQuery({
    queryKey: ['auth', 'me', scenario, role],
    queryFn: () => fetchAuthSnapshot({ scenario, role }),
    staleTime: 30_000,
    retry: false,
  })
}
