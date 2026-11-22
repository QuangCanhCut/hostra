import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  CheckCircle2,
  FileText,
  MessageSquareQuote,
  ShieldAlert,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Banner } from '@/components/ui/Banner'
import { Drawer } from '@/components/ui/Drawer'
import { Skeleton } from '@/components/ui/Skeleton'
import { useAuth } from '@/features/auth/hooks/useAuth'
import {
  useApproveKnowledgeBundle,
  useDecideKnowledgeItem,
  useKnowledgeDetail,
} from '@/features/knowledge/hooks/useKnowledge'
import { OCOP_STATUS_COPY } from '@/lib/status-copy'
import type { FactGroupKey } from '@/types/m02'

const FACT_GROUPS: Array<{ key: FactGroupKey | 'ALL'; label: string }> = [
  { key: 'ALL', label: 'Tất cả' },
  { key: 'PRICE', label: 'Giá bán' },
  { key: 'SPECS', label: 'Thông số' },
  { key: 'ORIGIN', label: 'Nguồn gốc' },
  { key: 'POLICY', label: 'Chính sách' },
  { key: 'MARKETING_CLAIMS', label: 'Marketing Claims' },
]

export function KnowledgeReviewPage() {
  const { skuId } = useParams<{ skuId: string }>()
  const { data: auth } = useAuth()
  const { data: pkg, isLoading } = useKnowledgeDetail(skuId)
  const decideMutation = useDecideKnowledgeItem(skuId ?? '')
  const approveBundleMutation = useApproveKnowledgeBundle(skuId ?? '')

  const [group, setGroup] = useState<FactGroupKey | 'ALL'>('ALL')
  const [mobileSourceOpen, setMobileSourceOpen] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const isOwner = Boolean(auth?.capabilities.canApproveContent)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (!pkg) {
    return <Card padding="lg">Không tìm thấy hồ sơ tri thức cho SKU này.</Card>
  }

  const ocop = OCOP_STATUS_COPY[pkg.ocopStatus]
  const visibleItems =
    group === 'ALL' ? pkg.items : pkg.items.filter((i) => i.group === group)
  const requiredItems = pkg.items.filter((i) => i.required)
  const approvedRequiredCount = requiredItems.filter((i) => i.decision === 'APPROVED').length
  const blockedCount = pkg.items.filter((i) => i.decision === 'BLOCKED').length
  const canApproveBundle =
    isOwner && approvedRequiredCount === requiredItems.length && requiredItems.length > 0

  const handleApproveBundle = async () => {
    setErrorMsg(null)
    setNotice(null)
    try {
      await approveBundleMutation.mutateAsync()
      setNotice(
        `Đã phê duyệt gói tri thức v${pkg.activeVersion + 1}. Các claim bị chặn đã được loại khỏi gói sử dụng. Lưu ý: phê duyệt tri thức không thay thế xác minh OCOP.`,
      )
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Không thể phê duyệt gói tri thức.')
    }
  }

  const sourceViewer = (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="text-xs font-semibold text-[var(--text-muted)]">Tài liệu nguồn (Chỉ đọc)</p>
          <p className="text-sm font-bold text-[var(--text-primary)]">{pkg.sourceDocTitle}</p>
        </div>
        <StatusBadge label={pkg.sourceDocVersion} tone="neutral" />
      </div>

      <div className="space-y-3">
        {pkg.sourceDocPassages.map((p, idx) => (
          <div
            key={idx}
            className="rounded-[10px] border border-[var(--border-default)] bg-[var(--bg-subtle)] p-3.5 space-y-1"
          >
            <p className="text-[11px] font-semibold text-[var(--text-muted)]">
              {p.page} · {p.heading}
            </p>
            <p className="text-xs text-[var(--text-primary)] leading-relaxed">{p.text}</p>
          </div>
        ))}
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Link
            to="/studio/knowledge"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] mb-1"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Quay lại Thư viện Tri thức
          </Link>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">
              Duyệt thông tin · {pkg.productName}
            </h1>
            <StatusBadge label={ocop.label} tone={ocop.tone} />
          </div>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            {pkg.skuCode} · Đối chiếu tài liệu nguồn bên trái và quyết định từng mục thông tin bên phải.
          </p>
        </div>

        <Button
          variant="secondary"
          size="sm"
          className="lg:hidden"
          leftIcon={<FileText className="h-4 w-4" />}
          onClick={() => setMobileSourceOpen(true)}
        >
          Xem tài liệu nguồn
        </Button>
      </div>

      {pkg.ocopStatus !== 'VERIFIED' ? (
        <Banner
          severity="info"
          title="Ranh giới OCOP độc lập"
          description="Bạn vẫn có thể rà soát và duyệt gói tri thức tại đây, nhưng sản phẩm này chưa đủ điều kiện lên sóng cho đến khi hồ sơ OCOP được xác minh hợp lệ."
        />
      ) : null}

      {notice ? <Banner severity="info" title="Đã phê duyệt gói tri thức" description={notice} /> : null}
      {errorMsg ? <Banner severity="danger" title="Không thể phê duyệt" description={errorMsg} /> : null}

      {/* Two-pane layout on desktop (KC-D1=A) */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <Card padding="md" className="hidden lg:block lg:col-span-5 h-fit sticky top-20">
          {sourceViewer}
        </Card>

        <div className="lg:col-span-7 space-y-5">
          {/* 5 groups filter (KC-D2=A) */}
          <div className="flex flex-wrap gap-2">
            {FACT_GROUPS.map((g) => (
              <button
                key={g.key}
                type="button"
                onClick={() => setGroup(g.key)}
                className={
                  group === g.key
                    ? 'h-9 rounded-full bg-[var(--brand-navy)] px-3.5 text-xs font-semibold text-white cursor-pointer'
                    : 'h-9 rounded-full border border-[var(--border-default)] bg-[var(--bg-surface)] px-3.5 text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] cursor-pointer'
                }
              >
                {g.label}
              </button>
            ))}
          </div>

          <div className="space-y-3">
            {visibleItems.map((item) => {
              const isBlocked = item.decision === 'BLOCKED'
              const badge =
                item.decision === 'APPROVED'
                  ? { label: 'Đã duyệt', tone: 'success' as const }
                  : item.decision === 'BLOCKED'
                    ? { label: 'Bị chặn', tone: 'danger' as const }
                    : item.decision === 'NEEDS_EVIDENCE'
                      ? { label: 'Thiếu nguồn', tone: 'warning' as const }
                      : item.decision === 'REJECTED'
                        ? { label: 'Từ chối', tone: 'neutral' as const }
                        : { label: 'Cần rà soát', tone: 'warning' as const }

              return (
                <Card key={item.id} padding="md" className="space-y-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="text-xs font-semibold text-[var(--text-muted)]">
                        {item.label} {item.required ? '· Bắt buộc' : ''}
                      </p>
                      <p className="mt-0.5 text-sm font-bold text-[var(--text-primary)]">
                        {item.proposedValue}
                      </p>
                    </div>
                    <StatusBadge label={badge.label} tone={badge.tone} />
                  </div>

                  <p className="text-xs text-[var(--text-secondary)] rounded-[8px] bg-[var(--bg-subtle)] px-3 py-2">
                    Nguồn trích dẫn: <span className="font-medium">{item.sourceFile} ({item.sourcePage})</span> — “{item.sourceExcerpt}”
                  </p>

                  {item.policyRiskNote ? (
                    <div className="flex items-start gap-2 rounded-[8px] border border-[var(--status-danger-border)] bg-[var(--status-danger-bg)] px-3 py-2 text-xs text-[var(--status-danger-fg)]">
                      <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
                      <span>{item.policyRiskNote}</span>
                    </div>
                  ) : null}

                  {!isBlocked ? (
                    <div className="flex flex-wrap gap-2 pt-1">
                      {isOwner ? (
                        <Button
                          size="sm"
                          variant={item.decision === 'APPROVED' ? 'secondary' : 'primary'}
                          loading={decideMutation.isPending}
                          onClick={() =>
                            decideMutation.mutate({ itemId: item.id, decision: 'APPROVED' })
                          }
                        >
                          Duyệt mục này
                        </Button>
                      ) : null}
                      <Button
                        size="sm"
                        variant="secondary"
                        loading={decideMutation.isPending}
                        onClick={() =>
                          decideMutation.mutate({ itemId: item.id, decision: 'NEEDS_EVIDENCE' })
                        }
                      >
                        Yêu cầu bổ sung nguồn
                      </Button>
                    </div>
                  ) : null}
                </Card>
              )
            })}
          </div>

          {/* Owner bundle approval footer (KC-D3=A) */}
          <Card padding="md" className="space-y-3 border-[var(--border-strong)]">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-bold text-[var(--text-primary)]">
                  Đã duyệt {approvedRequiredCount}/{requiredItems.length} mục bắt buộc
                </p>
                <p className="text-xs text-[var(--text-secondary)]">
                  {blockedCount > 0
                    ? `${blockedCount} claim không đủ bằng chứng sẽ tự động bị loại khỏi gói.`
                    : 'Không có claim bị chặn.'}
                </p>
              </div>
              {isOwner ? (
                <Button
                  variant="primary"
                  disabled={!canApproveBundle}
                  loading={approveBundleMutation.isPending}
                  leftIcon={<CheckCircle2 className="h-4 w-4" />}
                  onClick={handleApproveBundle}
                >
                  Phê duyệt gói tri thức
                </Button>
              ) : (
                <StatusBadge label="Chỉ Chủ sở hữu được phê duyệt" tone="neutral" />
              )}
            </div>
          </Card>

          {/* Text-only AI Speech Preview with sources (KC-D5=A) */}
          <Card padding="md" className="space-y-3">
            <div className="flex items-center gap-2">
              <MessageSquareQuote className="h-4 w-4 text-[var(--text-secondary)]" />
              <h2 className="text-sm font-bold text-[var(--text-primary)]">
                Xem trước lời AI dạng văn bản kèm trích dẫn nguồn
              </h2>
            </div>
            {pkg.speechPreviewLines.length === 0 ? (
              <p className="text-xs text-[var(--text-muted)]">
                Phê duyệt các mục bắt buộc để xem mẫu câu nói an toàn có trích dẫn nguồn (không cần tạo audio TTS).
              </p>
            ) : (
              <ul className="space-y-2.5">
                {pkg.speechPreviewLines.map((line, i) => (
                  <li key={i} className="rounded-[10px] bg-[var(--bg-subtle)] p-3 space-y-1">
                    <p className="text-sm text-[var(--text-primary)]">“{line.text}”</p>
                    <p className="text-[11px] font-medium text-[var(--text-muted)]">
                      Nguồn: {line.sourceRef}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          {/* Version History */}
          {pkg.versions.length > 0 ? (
            <Card padding="md" className="space-y-2.5">
              <h2 className="text-sm font-bold">Lịch sử phiên bản & So sánh thay đổi</h2>
              <ul className="divide-y divide-[var(--border-default)] text-xs">
                {pkg.versions.map((v) => (
                  <li key={v.version} className="py-2.5 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold">Phiên bản v{v.version} · {v.summary}</span>
                      <StatusBadge
                        label={v.status === 'APPROVED' ? 'Đang áp dụng' : 'Bản cũ'}
                        tone={v.status === 'APPROVED' ? 'success' : 'neutral'}
                      />
                    </div>
                    {v.beforeValue && v.afterValue ? (
                      <p className="text-[var(--text-secondary)]">
                        Trước: <span className="line-through">{v.beforeValue}</span> → Sau:{' '}
                        <span className="font-semibold text-[var(--text-primary)]">{v.afterValue}</span>
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            </Card>
          ) : null}
        </div>
      </div>

      <Drawer
        open={mobileSourceOpen}
        onClose={() => setMobileSourceOpen(false)}
        title="Tài liệu nguồn sản phẩm"
        subtitle={pkg.sourceDocTitle}
      >
        {sourceViewer}
      </Drawer>
    </div>
  )
}
