import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useScenario } from '@/hooks/useScenario'
import {
  createProduct,
  fetchProductById,
  fetchProducts,
  simulateReviewerVerdict,
  submitProductOcop,
  uploadProductEvidence,
} from '@/features/products/services/products.service'
import type { ProductDraftPayload } from '@/types/m02'

export function useProducts() {
  const { scenario, role } = useScenario()
  return useQuery({
    queryKey: ['products', scenario, role],
    queryFn: () => fetchProducts({ scenario, role }),
    retry: false,
  })
}

export function useProductDetail(skuId: string | undefined) {
  const { scenario, role } = useScenario()
  return useQuery({
    queryKey: ['products', skuId, scenario, role],
    queryFn: () => fetchProductById(skuId!, { scenario, role }),
    enabled: Boolean(skuId),
    retry: false,
  })
}

export function useCreateProduct() {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: ProductDraftPayload & { submitForVerification?: boolean }) =>
      createProduct(payload, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['products'] })
      qc.invalidateQueries({ queryKey: ['knowledge'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useUploadProductEvidence(skuId: string) {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: {
      fileName: string
      documentType: 'OCOP_CERT' | 'FOOD_SAFETY' | 'PRODUCT_LABEL' | 'ORIGIN_DOC'
    }) => uploadProductEvidence(skuId, payload, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['products'] })
    },
  })
}

export function useSubmitProductOcop(skuId: string) {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => submitProductOcop(skuId, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['products'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useSimulateReviewerVerdict(skuId: string) {
  const { scenario, role } = useScenario()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (verdict: 'VERIFIED' | 'PENDING_REVIEW' | 'REJECTED' | 'REVOKED') =>
      simulateReviewerVerdict(skuId, verdict, { scenario, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['products'] })
      qc.invalidateQueries({ queryKey: ['knowledge'] })
      qc.invalidateQueries({ queryKey: ['readiness'] })
      qc.invalidateQueries({ queryKey: ['sessions'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
