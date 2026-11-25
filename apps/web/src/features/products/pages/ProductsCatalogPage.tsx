import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, PackageCheck, Plus, Search } from 'lucide-react'
import { ButtonLink } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import {
  DataTable,
  TABLE_BODY_CLASS,
  TABLE_HEAD_ROW_CLASS,
  TABLE_ROW_HOVER_CLASS,
} from '@/components/ui/DataTable'
import { PageHeader } from '@/components/ui/PageHeader'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { ProductThumb } from '@/components/shared/PortraitAvatar'
import { useProducts } from '@/features/products/hooks/useProducts'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { OCOP_STATUS_COPY } from '@/lib/status-copy'
import { formatVnd } from '@/lib/format'

type OcopFilter = 'ALL' | 'VERIFIED' | 'PENDING_REVIEW'

export function ProductsCatalogPage() {
  const { data: auth } = useAuth()
  const { data, isLoading } = useProducts()
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<OcopFilter>('ALL')

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-52" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  const items = data?.items ?? []
  const filtered = items.filter((item) => {
    const q = search.trim().toLowerCase()
    const matchText =
      !q ||
      item.name.toLowerCase().includes(q) ||
      item.skuCode.toLowerCase().includes(q)
    const matchFilter = filter === 'ALL' || item.ocopStatus === filter
    return matchText && matchFilter
  })

  const isOwner = Boolean(auth?.capabilities.canSubmitOcop)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Sản phẩm & Hồ sơ OCOP"
        subtitle="Quản lý danh mục sản phẩm thực phẩm đóng gói. Trạng thái OCOP và Tri thức được theo dõi độc lập."
        actions={
          <ButtonLink
            to="/studio/products/new"
            variant="primary"
            leftIcon={<Plus className="h-4 w-4" />}
          >
            {isOwner ? 'Thêm sản phẩm mới' : 'Tạo bản nháp sản phẩm'}
          </ButtonLink>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-xs">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]"
            aria-hidden="true"
          />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm theo tên hoặc mã SKU..."
            className="min-h-[42px] w-full rounded-[8px] border border-[var(--border-default)] bg-[var(--bg-canvas)] pl-9 pr-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)]/70 focus:border-[var(--border-strong)]"
          />
        </div>

        <div className="flex flex-wrap gap-2">
          {(
            [
              ['ALL', 'Tất cả'],
              ['VERIFIED', 'OCOP đã xác minh'],
              ['PENDING_REVIEW', 'Chờ xác minh OCOP'],
            ] as Array<[OcopFilter, string]>
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => setFilter(key)}
              className={
                filter === key
                  ? 'min-h-9 rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-raised)] px-3.5 text-xs font-semibold text-[var(--accent-gold)] cursor-pointer'
                  : 'min-h-9 rounded-[8px] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3.5 text-xs font-medium text-[var(--text-muted)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)] cursor-pointer'
              }
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={<PackageCheck className="h-6 w-6" />}
          title={
            items.length === 0
              ? 'Chưa có sản phẩm nào trong danh mục'
              : 'Không có sản phẩm phù hợp bộ lọc'
          }
          description="Thêm 2–5 sản phẩm thực phẩm đóng gói cùng hồ sơ OCOP để chuẩn bị cho phiên livestream."
          action={
            <ButtonLink
              to="/studio/products/new"
              variant="primary"
              leftIcon={<Plus className="h-4 w-4" />}
            >
              Thêm sản phẩm
            </ButtonLink>
          }
        />
      ) : (
        <>
          {/* Wide desktop table */}
          <DataTable className="hidden xl:block">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className={TABLE_HEAD_ROW_CLASS}>
                  <th className="px-5 py-3.5">Sản phẩm &amp; SKU</th>
                  <th className="px-4 py-3.5">Giá niêm yết</th>
                  <th className="px-4 py-3.5">Xác minh OCOP</th>
                  <th className="px-4 py-3.5">Tri thức &amp; Claims</th>
                  <th className="px-4 py-3.5">Điều kiện phiên</th>
                  <th className="px-5 py-3.5 text-right">Thao tác</th>
                </tr>
              </thead>
              <tbody className={TABLE_BODY_CLASS}>
                {filtered.map((item) => {
                  const ocop = OCOP_STATUS_COPY[item.ocopStatus]
                  const knowledgeTone =
                    item.knowledgeStatus === 'APPROVED' ? 'success' : 'warning'
                  const knowledgeLabel =
                    item.knowledgeStatus === 'APPROVED' ? 'Tri thức đã duyệt' : 'Chờ duyệt tri thức'

                  return (
                    <tr key={item.skuId} className={TABLE_ROW_HOVER_CLASS}>
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-3">
                          <ProductThumb skuId={item.skuId} name={item.name} />
                          <div className="min-w-0">
                            <p className="font-semibold text-[var(--text-primary)]">{item.name}</p>
                            <p className="text-xs text-[var(--text-muted)]">
                              {item.skuCode} · {item.packSpec}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap font-semibold tabular-nums text-[var(--text-primary)]">
                        {formatVnd(item.priceVnd)}
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <StatusBadge
                          label={
                            item.ocopStatus === 'VERIFIED' && item.ocopStars
                              ? `OCOP ${item.ocopStars} sao · Đã xác minh`
                              : ocop.label
                          }
                          tone={ocop.tone}
                          className="whitespace-nowrap"
                        />
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <StatusBadge
                          label={knowledgeLabel}
                          tone={knowledgeTone}
                          className="whitespace-nowrap"
                        />
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <StatusBadge
                          label={item.sessionEligible ? 'Đủ điều kiện chọn' : 'Chưa đủ điều kiện'}
                          tone={item.sessionEligible ? 'success' : 'neutral'}
                          className="whitespace-nowrap"
                        />
                      </td>
                      <td className="px-5 py-3.5 text-right whitespace-nowrap">
                        <Link
                          to={`/studio/products/${item.skuId}`}
                          className="inline-flex min-h-9 items-center gap-1 rounded-[8px] border border-[var(--border-strong)] px-3 py-1.5 text-xs font-semibold text-[var(--text-primary)] transition-colors hover:border-[var(--accent-gold)] hover:bg-[var(--bg-raised)]"
                        >
                          Chi tiết <ArrowRight className="h-3.5 w-3.5" />
                        </Link>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </DataTable>

          {/* Tablet & Mobile cards */}
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:hidden">
            {filtered.map((item) => {
              const ocop = OCOP_STATUS_COPY[item.ocopStatus]
              return (
                <Card key={item.skuId} padding="sm" className="space-y-3">
                  <div className="flex items-start gap-3">
                    <ProductThumb skuId={item.skuId} name={item.name} />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-semibold text-[var(--text-muted)]">{item.skuCode}</p>
                      <p className="text-sm font-bold text-[var(--text-primary)]">{item.name}</p>
                      <p className="mt-0.5 text-xs font-semibold tabular-nums text-[var(--text-secondary)]">
                        {formatVnd(item.priceVnd)} · {item.packSpec}
                      </p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    <StatusBadge label={ocop.label} tone={ocop.tone} />
                    <StatusBadge
                      label={item.knowledgeStatus === 'APPROVED' ? 'Tri thức đã duyệt' : 'Chờ duyệt tri thức'}
                      tone={item.knowledgeStatus === 'APPROVED' ? 'success' : 'warning'}
                    />
                  </div>
                  <div className="pt-2 border-t border-[var(--border-default)] flex justify-end">
                    <Link
                      to={`/studio/products/${item.skuId}`}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--text-primary)]"
                    >
                      Mở hồ sơ sản phẩm <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                </Card>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
