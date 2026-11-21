import { apiRequest, type RequestContext } from '@/services/api-client'
import type { ProductDetail, ProductDraftPayload } from '@/types/m02'

export function fetchProducts(
  context: RequestContext,
): Promise<{ items: ProductDetail[] }> {
  return apiRequest<{ items: ProductDetail[] }>('/api/mock/v1/products', context)
}

export function fetchProductById(
  skuId: string,
  context: RequestContext,
): Promise<ProductDetail> {
  return apiRequest<ProductDetail>(`/api/mock/v1/products/${skuId}`, context)
}

export function createProduct(
  payload: ProductDraftPayload & { submitForVerification?: boolean },
  context: RequestContext,
): Promise<ProductDetail> {
  return apiRequest<ProductDetail>('/api/mock/v1/products', context, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function uploadProductEvidence(
  skuId: string,
  payload: {
    fileName: string
    documentType: 'OCOP_CERT' | 'FOOD_SAFETY' | 'PRODUCT_LABEL' | 'ORIGIN_DOC'
  },
  context: RequestContext,
): Promise<ProductDetail> {
  return apiRequest<ProductDetail>(`/api/mock/v1/products/${skuId}/evidence`, context, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function submitProductOcop(
  skuId: string,
  context: RequestContext,
): Promise<ProductDetail> {
  return apiRequest<ProductDetail>(`/api/mock/v1/products/${skuId}/submit-ocop`, context, {
    method: 'POST',
  })
}

export function simulateReviewerVerdict(
  skuId: string,
  verdict: 'VERIFIED' | 'PENDING_REVIEW' | 'REJECTED' | 'REVOKED',
  context: RequestContext,
): Promise<ProductDetail> {
  return apiRequest<ProductDetail>(
    `/api/mock/v1/products/${skuId}/mock-reviewer-verdict`,
    context,
    {
      method: 'POST',
      body: JSON.stringify({ verdict }),
    },
  )
}
