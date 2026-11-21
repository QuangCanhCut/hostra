import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft,
  BookOpenCheck,
  CheckCircle2,
  Circle,
  FileText,
  Send,
  ShieldCheck,
  Upload,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Banner } from '@/components/ui/Banner'
import { Tabs } from '@/components/ui/Tabs'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { ProductThumb } from '@/components/shared/PortraitAvatar'
import { useAuth } from '@/features/auth/hooks/useAuth'
import {
  useProductDetail,
  useSimulateReviewerVerdict,
  useSubmitProductOcop,
  useUploadProductEvidence,
} from '@/features/products/hooks/useProducts'
import { OCOP_STATUS_COPY } from '@/lib/status-copy'
import { formatShortTime, formatVnd } from '@/lib/format'

type TabKey = 'overview' | 'ocop' | 'facts' | 'versions'

export function ProductDetailPage() {
  const { skuId } = useParams<{ skuId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = (searchParams.get('tab') as TabKey) || 'overview'

  const { data: auth } = useAuth()
  const { data: product, isLoading } = useProductDetail(skuId)
  const uploadMutation = useUploadProductEvidence(skuId ?? '')
  const submitMutation = useSubmitProductOcop(skuId ?? '')
  const reviewerMutation = useSimulateReviewerVerdict(skuId ?? '')

  const [notice, setNotice] = useState<string | null>(null)
  const isOwner = Boolean(auth?.capabilities.canSubmitOcop)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-72 w-full" />
      </div>
    )
  }

  if (!product) {
    return (
      <EmptyState
        icon={<FileText className="h-6 w-6" />}
        title="Không tìm thấy sản phẩm"
        description="Sản phẩm này không tồn tại trong danh mục workspace."
        action={
          <Link to="/studio/products">
            <Button variant="secondary">Quay lại Danh mục</Button>
          </Link>
        }
      />
    )
  }

  const ocop = OCOP_STATUS_COPY[product.ocopStatus]
  const setTab = (tab: TabKey) => {
    setSearchParams({ tab })
  }

  const handleUploadDemoDoc = async (docType: 'OCOP_CERT' | 'ORIGIN_DOC') => {
    await uploadMutation.mutateAsync({
      fileName:
        docType === 'OCOP_CERT'
          ? `Quyet_dinh_OCOP_${product.skuCode}_bo_sung.pdf`
          : `Chung_tu_phan_phoi_${product.skuCode}.pdf`,
      documentType: docType,
    })
    setNotice('Đã bổ sung tài liệu vào hồ sơ nháp. Tài liệu mới tải lên không tự chuyển trạng thái thành OCOP đã xác minh.')
  }

  const handleSubmitOcop = async () => {
    await submitMutation.mutateAsync()
    setNotice('Chủ sở hữu đã gửi hồ sơ đề nghị xác minh OCOP. Hệ thống chờ Reviewer P09 đối chiếu độc lập.')
  }

  return (
    <div className="space-y-6">
      <div>
        <Link
          to="/studio/products"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] mb-2"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Quay lại Danh mục sản phẩm
        </Link>

        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3.5">
            <ProductThumb skuId={product.skuId} name={product.name} className="h-14 w-14" />
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-bold text-[var(--text-primary)]">{product.name}</h1>
                <StatusBadge label={ocop.label} tone={ocop.tone} />
              </div>
              <p className="mt-0.5 text-sm text-[var(--text-secondary)]">
                {product.skuCode} · {formatVnd(product.priceVnd)} · {product.packSpec}
              </p>
            </div>
          </div>

          <Link to={`/studio/knowledge/${product.skuId}`}>
            <Button variant="secondary" size="sm" leftIcon={<BookOpenCheck className="h-4 w-4" />}>
              Mở Tri thức & Claims
            </Button>
          </Link>
        </div>
      </div>

      {notice ? <Banner severity="info" title="Cập nhật hồ sơ" description={notice} /> : null}

      <Tabs<TabKey>
        activeId={activeTab}
        onChange={setTab}
        items={[
          { id: 'overview', label: 'Tổng quan' },
          { id: 'ocop', label: 'Hồ sơ OCOP', count: product.evidenceFiles.length },
          { id: 'facts', label: 'Tri thức & Facts' },
          { id: 'versions', label: 'Phiên bản', count: product.versions.length },
        ]}
      />

      {activeTab === 'overview' ? (
        <Card padding="lg" className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <div>
            <p className="text-xs text-[var(--text-muted)]">Thương hiệu / Chủ thể</p>
            <p className="mt-0.5 text-sm font-semibold">{product.brandName}</p>
          </div>
          <div>
            <p className="text-xs text-[var(--text-muted)]">Xuất xứ</p>
            <p className="mt-0.5 text-sm font-semibold">{product.origin}</p>
          </div>
          <div>
            <p className="text-xs text-[var(--text-muted)]">Hạn sử dụng</p>
            <p className="mt-0.5 text-sm font-semibold">{product.expiryLabel}</p>
          </div>
          <div>
            <p className="text-xs text-[var(--text-muted)]">Phiên đang sử dụng</p>
            <p className="mt-0.5 text-sm font-semibold">
              {product.linkedSessionCodes.length > 0 ? product.linkedSessionCodes.join(', ') : 'Chưa gắn vào phiên nào'}
            </p>
          </div>
          <div className="sm:col-span-2">
            <p className="text-xs text-[var(--text-muted)]">Mô tả sản phẩm</p>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">{product.description}</p>
          </div>
        </Card>
      ) : null}

      {activeTab === 'ocop' ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="lg:col-span-7 space-y-4">
            <Card padding="md" className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-base font-bold">Tài liệu chứng cứ OCOP & Thực phẩm</h2>
                <StatusBadge label={ocop.label} tone={ocop.tone} />
              </div>

              <div className="rounded-[12px] border-2 border-dashed border-[var(--border-strong)] bg-[var(--bg-subtle)] p-5 text-center space-y-2">
                <Upload className="mx-auto h-6 w-6 text-[var(--text-secondary)]" />
                <p className="text-sm font-semibold">Bổ sung tài liệu chứng minh</p>
                <p className="text-xs text-[var(--text-muted)]">
                  Cả Chủ sở hữu và Vận hành viên được phép tải tài liệu nháp. Chỉ Chủ sở hữu được Gửi xác minh.
                </p>
                <div className="flex flex-wrap justify-center gap-2 pt-1">
                  <Button
                    variant="secondary"
                    size="sm"
                    loading={uploadMutation.isPending}
                    onClick={() => handleUploadDemoDoc('OCOP_CERT')}
                  >
                    + Tải Quyết định OCOP mẫu
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    loading={uploadMutation.isPending}
                    onClick={() => handleUploadDemoDoc('ORIGIN_DOC')}
                  >
                    + Tải Chứng từ phân phối mẫu
                  </Button>
                </div>
              </div>

              {product.evidenceFiles.length === 0 ? (
                <p className="text-xs text-[var(--text-muted)]">Chưa có tài liệu nào được tải lên.</p>
              ) : (
                <ul className="divide-y divide-[var(--border-default)]">
                  {product.evidenceFiles.map((file) => (
                    <li key={file.id} className="flex items-center justify-between gap-3 py-3 text-xs">
                      <div className="min-w-0">
                        <p className="font-semibold text-[var(--text-primary)] truncate">{file.fileName}</p>
                        <p className="text-[var(--text-muted)]">
                          {file.documentTypeLabel} · Tải bởi {file.uploadedBy} · {file.sizeKb} KB
                        </p>
                      </div>
                      <StatusBadge label="Đã lưu" tone="neutral" />
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>

          <div className="lg:col-span-5 space-y-4">
            <Card padding="md" className="space-y-4">
              <h2 className="text-base font-bold">Kiểm tra hồ sơ & Kết quả xác minh</h2>
              <p className="text-xs text-[var(--text-secondary)] rounded-[8px] bg-[var(--bg-subtle)] p-3">
                {product.ocopReasonNote}
              </p>

              <ul className="space-y-2">
                {product.missingChecklist.map((item) => (
                  <li key={item.id} className="flex items-center gap-2 text-xs">
                    {item.satisfied ? (
                      <CheckCircle2 className="h-4 w-4 text-[var(--status-success-fg)] shrink-0" />
                    ) : (
                      <Circle className="h-4 w-4 text-[var(--status-warning-fg)] shrink-0" />
                    )}
                    <span className={item.satisfied ? 'text-[var(--text-primary)]' : 'text-[var(--status-warning-fg)] font-medium'}>
                      {item.label}
                    </span>
                  </li>
                ))}
              </ul>

              {isOwner ? (
                <Button
                  variant="primary"
                  className="w-full"
                  loading={submitMutation.isPending}
                  leftIcon={<Send className="h-4 w-4" />}
                  onClick={handleSubmitOcop}
                >
                  Gửi hồ sơ xác minh OCOP (Chủ sở hữu)
                </Button>
              ) : (
                <p className="text-xs text-[var(--text-muted)]">
                  Vận hành viên không có quyền gửi xác minh OCOP. Vui lòng thông báo Chủ sở hữu rà soát.
                </p>
              )}
            </Card>

            {/* Independent Reviewer Mock Simulator (clearly separated from Merchant actions) */}
            <Card padding="md" className="border-dashed space-y-3 bg-[var(--bg-subtle)]">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-[var(--text-secondary)]" />
                <h3 className="text-xs font-bold text-[var(--text-primary)]">
                  Mô phỏng kết quả từ Reviewer / Hệ thống P09 (Dev)
                </h3>
              </div>
              <p className="text-[11px] text-[var(--text-muted)]">
                Merchant không tự đặt OCOP thành Đã xác minh. Các nút dưới đây chỉ mô phỏng phản hồi từ thẩm quyền P09 để kiểm thử Readiness.
              </p>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  loading={reviewerMutation.isPending}
                  onClick={() => reviewerMutation.mutate('VERIFIED')}
                >
                  P09: Xác minh đạt
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  loading={reviewerMutation.isPending}
                  onClick={() => reviewerMutation.mutate('PENDING_REVIEW')}
                >
                  P09: Chờ bổ sung
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  loading={reviewerMutation.isPending}
                  onClick={() => reviewerMutation.mutate('REJECTED')}
                >
                  P09: Từ chối
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  loading={reviewerMutation.isPending}
                  onClick={() => reviewerMutation.mutate('REVOKED')}
                >
                  P09: Thu hồi OCOP
                </Button>
              </div>
            </Card>
          </div>
        </div>
      ) : null}

      {activeTab === 'facts' ? (
        <Card padding="lg" className="space-y-3">
          <h2 className="text-base font-bold">Liên kết Tri thức & Claims của {product.skuCode}</h2>
          <p className="text-sm text-[var(--text-secondary)]">
            Trạng thái hiện tại:{' '}
            <span className="font-semibold text-[var(--text-primary)]">
              {product.knowledgeStatus === 'APPROVED' ? 'Đã phê duyệt gói tri thức' : 'Đang chờ rà soát & phê duyệt'}
            </span>
            . Phê duyệt tri thức không thay thế xác minh OCOP.
          </p>
          <Link to={`/studio/knowledge/${product.skuId}`}>
            <Button variant="primary">Đi tới trang đối chiếu Tri thức & Claims</Button>
          </Link>
        </Card>
      ) : null}

      {activeTab === 'versions' ? (
        <Card padding="md">
          <ul className="divide-y divide-[var(--border-default)]">
            {product.versions.map((v) => (
              <li key={v.version} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
                <div>
                  <p className="font-semibold">Phiên bản v{v.version} · {v.summary}</p>
                  <p className="text-xs text-[var(--text-muted)]">Thực hiện bởi {v.actorName}</p>
                </div>
                <span className="text-xs text-[var(--text-muted)] tabular-nums">
                  {formatShortTime(v.updatedAt)}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}
    </div>
  )
}
