import type { AuthSnapshot } from '@/types/auth'
import { apiRequest, type RequestContext } from '@/services/api-client'

export function fetchAuthSnapshot(context: RequestContext): Promise<AuthSnapshot> {
  return apiRequest<AuthSnapshot>('/api/mock/v1/auth/me', context)
}
