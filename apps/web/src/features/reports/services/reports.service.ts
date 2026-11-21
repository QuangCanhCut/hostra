import { apiRequest, type RequestContext } from '@/services/api-client'
import type { SessionReportDetail } from '@/types/m03'

export function fetchSessionReport(
  sessionId: string,
  context: RequestContext,
): Promise<SessionReportDetail> {
  return apiRequest<SessionReportDetail>(`/api/mock/v1/reports/${sessionId}`, context)
}
