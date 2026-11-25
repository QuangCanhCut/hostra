import { apiRequest, type RequestContext } from '@/services/api-client'
import type { DashboardSnapshot } from '@/features/dashboard/types/dashboard.types'

export function fetchDashboardSnapshot(
  context: RequestContext,
): Promise<DashboardSnapshot> {
  return apiRequest<DashboardSnapshot>('/api/mock/v1/dashboard', context)
}
