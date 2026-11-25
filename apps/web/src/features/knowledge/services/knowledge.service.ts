import { apiRequest, type RequestContext } from '@/services/api-client'
import type { FactDecisionStatus, KnowledgePackageDetail } from '@/types/m02'

export function fetchKnowledgeList(
  context: RequestContext,
): Promise<{ items: KnowledgePackageDetail[] }> {
  return apiRequest<{ items: KnowledgePackageDetail[] }>('/api/mock/v1/knowledge', context)
}

export function fetchKnowledgeBySku(
  skuId: string,
  context: RequestContext,
): Promise<KnowledgePackageDetail> {
  return apiRequest<KnowledgePackageDetail>(`/api/mock/v1/knowledge/${skuId}`, context)
}

export function decideKnowledgeItem(
  skuId: string,
  itemId: string,
  payload: { decision: FactDecisionStatus; proposedValue?: string },
  context: RequestContext,
): Promise<KnowledgePackageDetail> {
  return apiRequest<KnowledgePackageDetail>(
    `/api/mock/v1/knowledge/${skuId}/items/${itemId}/decision`,
    context,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  )
}

export function approveKnowledgeBundle(
  skuId: string,
  context: RequestContext,
): Promise<KnowledgePackageDetail> {
  return apiRequest<KnowledgePackageDetail>(
    `/api/mock/v1/knowledge/${skuId}/approve-bundle`,
    context,
    { method: 'POST' },
  )
}
