import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, BookOpenCheck, Search } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { PageHeader } from '@/components/ui/PageHeader'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { useKnowledgeList } from '@/features/knowledge/hooks/useKnowledge'
import { OCOP_STATUS_COPY } from '@/lib/status-copy'

export function KnowledgeLibraryPage() {
  const { data, isLoading } = useKnowledgeList()
  const [search, setSearch] = useState('')

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-52" />
        <Skeleton className="h-56 w-full" />
      </div>
    )
  }

  const items = data?.items ?? []
  const filtered = items.filter((k) => {
    const q = search.trim().toLowerCase()
    return !q || k.productName.toLowerCase().includes(q) || k.skuCode.toLowerCase().includes(q)
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Tri thức sản phẩm & Claims"
        subtitle="Đối chiếu tài liệu nguồn với từng nhóm thông tin (Giá, Thông số, Nguồn gốc, Chính sách, Marketing Claims) trước khi phê duyệt."
      />

      <div className="relative max-w-xs">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Tìm SKU hoặc tên sản phẩm..."
          className="min-h-[42px] w-full rounded-[8px] border border-[var(--border-default)] bg-[var(--bg-canvas)] pl-9 pr-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)]/70 focus:border-[var(--border-strong)]"
        />
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={<BookOpenCheck className="h-6 w-6" />}
          title="Chưa có hồ sơ tri thức nào"
          description="Thêm sản phẩm và tải tài liệu để bắt đầu rà soát tri thức."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {filtered.map((pkg) => {
            const blockedCount = pkg.items.filter((i) => i.decision === 'BLOCKED').length
            const pendingCount = pkg.items.filter(
              (i) => i.required && i.decision !== 'APPROVED',
            ).length
            const ocop = OCOP_STATUS_COPY[pkg.ocopStatus]

            return (
              <Card key={pkg.skuId} padding="md" className="flex flex-col justify-between gap-4">
                <div className="space-y-2.5">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-xs font-semibold text-[var(--text-muted)]">
                        {pkg.skuCode} · Phiên bản đã duyệt: v{pkg.activeVersion}
                      </p>
                      <h2 className="text-base font-bold text-[var(--text-primary)]">
                        {pkg.productName}
                      </h2>
                    </div>
                    <StatusBadge
                      label={pkg.approvalStatus === 'APPROVED' ? 'Đã phê duyệt' : 'Cần rà soát'}
                      tone={pkg.approvalStatus === 'APPROVED' ? 'success' : 'warning'}
                    />
                  </div>

                  <p className="text-xs text-[var(--text-secondary)]">
                    Tài liệu nguồn: <span className="font-medium text-[var(--text-primary)]">{pkg.sourceDocTitle}</span>
                  </p>

                  <div className="flex flex-wrap gap-1.5">
                    <StatusBadge label={ocop.label} tone={ocop.tone} />
                    {pendingCount > 0 ? (
                      <StatusBadge label={`${pendingCount} mục cần duyệt`} tone="warning" />
                    ) : null}
                    {blockedCount > 0 ? (
                      <StatusBadge label={`${blockedCount} claim bị chặn`} tone="danger" />
                    ) : null}
                  </div>
                </div>

                <div className="pt-2 border-t border-[var(--border-default)] flex justify-end">
                  <Link
                    to={`/studio/knowledge/${pkg.skuId}`}
                    className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--text-primary)] hover:underline"
                  >
                    Đối chiếu tài liệu & Duyệt <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
