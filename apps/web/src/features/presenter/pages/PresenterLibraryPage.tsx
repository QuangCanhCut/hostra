import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, Plus, Search, ShieldAlert, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { Banner } from '@/components/ui/Banner'
import { PresenterPortrait } from '@/components/shared/PortraitAvatar'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { usePresenters } from '@/features/presenter/hooks/usePresenters'
import { RIGHTS_STATUS_COPY } from '@/lib/status-copy'
import type { PresenterDetail } from '@/types/m02'

type FilterKey = 'ALL' | 'APPROVED' | 'PENDING_RIGHTS' | 'GENERATING' | 'REVOKED'

function matchesFilter(item: PresenterDetail, filter: FilterKey): boolean {
  if (filter === 'ALL') return true
  if (filter === 'APPROVED') return item.approvalStatus === 'APPROVED' && item.rightsStatus === 'VERIFIED'
  if (filter === 'PENDING_RIGHTS') return item.rightsStatus === 'PENDING' || item.rightsStatus === 'MISSING'
  if (filter === 'GENERATING') return item.generationState === 'RUNNING' || item.qcStatus === 'FAIL_PARTIAL'
  if (filter === 'REVOKED') return item.rightsStatus === 'REVOKED' || item.rightsStatus === 'EXPIRED'
  return true
}

export function PresenterLibraryPage() {
  const { data: auth } = useAuth()
  const { data, isLoading, isError, refetch } = usePresenters()
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<FilterKey>('ALL')

  const canManage = Boolean(auth?.capabilities.canManagePresenters)

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-52" />
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
          {[1, 2, 3].map((n) => (
            <Card key={n} padding="md" className="space-y-3">
              <Skeleton className="aspect-[4/3] w-full" />
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-4 w-full" />
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <EmptyState
        tone="danger"
        icon={<AlertTriangle className="h-6 w-6" />}
        title="Không thể tải thư viện AI Presenter"
        description="Kết nối dữ liệu tạm thời bị gián đoạn. Vui lòng thử tải lại."
        action={<Button onClick={() => refetch()}>Thử tải lại</Button>}
      />
    )
  }

  const items = data?.items ?? []
  const revokedCount = items.filter((p) => p.rightsStatus === 'REVOKED').length
  const filtered = items.filter((item) => {
    const q = search.trim().toLowerCase()
    const matchText =
      !q ||
      item.displayName.toLowerCase().includes(q) ||
      item.styleLabel.toLowerCase().includes(q)
    return matchText && matchesFilter(item, filter)
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            Thư viện AI Presenter
          </h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Duyệt người dẫn AI, theo dõi quyền sử dụng độc lập và quản lý các phiên bản đã tạo.
          </p>
        </div>

        {canManage ? (
          <Link to="/studio/presenters/new">
            <Button variant="primary" leftIcon={<Plus className="h-4 w-4" />}>
              Tạo Presenter mới
            </Button>
          </Link>
        ) : null}
      </div>

      {revokedCount > 0 ? (
        <Banner
          severity="danger"
          title="Có AI Presenter bị thu hồi quyền sử dụng"
          description="Quyền hình ảnh bị thu hồi sẽ tự động khóa sử dụng tài sản liên quan trong các phiên livestream mới."
        />
      ) : null}

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
            placeholder="Tìm theo tên hoặc phong cách..."
            className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] pl-9 pr-3 text-sm text-[var(--text-primary)]"
          />
        </div>

        <div className="flex flex-wrap gap-2">
          {(
            [
              ['ALL', 'Tất cả'],
              ['APPROVED', 'Đã duyệt'],
              ['PENDING_RIGHTS', 'Chờ quyền'],
              ['GENERATING', 'Đang tạo / QC'],
              ['REVOKED', 'Đã thu hồi'],
            ] as Array<[FilterKey, string]>
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => setFilter(key)}
              className={
                filter === key
                  ? 'h-9 rounded-full bg-[var(--brand-navy)] px-3.5 text-xs font-semibold text-white cursor-pointer'
                  : 'h-9 rounded-full border border-[var(--border-default)] bg-[var(--bg-surface)] px-3.5 text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] cursor-pointer'
              }
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={<Sparkles className="h-6 w-6" />}
          title={
            items.length === 0
              ? 'Bạn chưa có AI Presenter nào'
              : 'Không tìm thấy Presenter phù hợp bộ lọc'
          }
          description={
            items.length === 0
              ? 'Tạo AI Presenter từ ảnh chân dung có xác nhận quyền hợp lệ của chủ thể.'
              : 'Thử thay đổi từ khóa tìm kiếm hoặc chọn lại trạng thái lọc.'
          }
          action={
            items.length === 0 && canManage ? (
              <Link to="/studio/presenters/new">
                <Button variant="primary" leftIcon={<Plus className="h-4 w-4" />}>
                  Tạo Presenter đầu tiên
                </Button>
              </Link>
            ) : undefined
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((item) => {
            const rightsCopy = RIGHTS_STATUS_COPY[item.rightsStatus]
            const approvalBadge =
              item.rightsStatus === 'REVOKED'
                ? { label: 'Đã khóa sử dụng', tone: 'danger' as const }
                : item.approvalStatus === 'APPROVED'
                  ? { label: 'Đã duyệt', tone: 'success' as const }
                  : item.qcStatus === 'FAIL_PARTIAL'
                    ? { label: 'Cần tạo lại clip lỗi', tone: 'warning' as const }
                    : { label: 'Chưa duyệt', tone: 'neutral' as const }

            return (
              <Card key={item.id} padding="md" className="flex flex-col justify-between gap-4">
                <div className="space-y-3.5">
                  <PresenterPortrait presenterId={item.id} name={item.displayName} />

                  <div className="space-y-1">
                    <div className="flex items-start justify-between gap-2">
                      <h2 className="text-base font-bold text-[var(--text-primary)] leading-snug">
                        {item.displayName}
                      </h2>
                      <span className="rounded-[6px] bg-[var(--bg-subtle)] px-2 py-0.5 text-xs font-semibold text-[var(--text-secondary)] tabular-nums shrink-0">
                        {item.activePackVersion}
                      </span>
                    </div>
                    <p className="text-xs text-[var(--text-secondary)]">
                      Phong cách: <span className="font-medium text-[var(--text-primary)]">{item.styleLabel}</span>
                    </p>
                    <p className="text-xs text-[var(--text-muted)]">{item.voicePresetLabel}</p>
                  </div>

                  <div className="flex flex-wrap gap-1.5">
                    <StatusBadge label={approvalBadge.label} tone={approvalBadge.tone} />
                    <StatusBadge label={rightsCopy.label} tone={rightsCopy.tone} />
                  </div>

                  <p className="text-xs text-[var(--text-secondary)] rounded-[8px] bg-[var(--bg-subtle)] px-3 py-2">
                    {item.jobStageLabel}
                  </p>
                </div>

                <div className="flex items-center gap-2 pt-2 border-t border-[var(--border-default)]">
                  <Link to={`/studio/presenters/${item.id}`} className="flex-1">
                    <Button variant="secondary" size="sm" className="w-full">
                      Xem chi tiết & QC
                    </Button>
                  </Link>
                  {item.rightsStatus === 'PENDING' ? (
                    <Link to={`/rights/consent/${item.rightsConsent.requestId}`}>
                      <Button variant="ghost" size="sm" leftIcon={<ShieldAlert className="h-3.5 w-3.5" />}>
                        Cổng quyền
                      </Button>
                    </Link>
                  ) : null}
                </div>
              </Card>
            )
          })}
        </div>
      )}

      <Card padding="sm" className="bg-[var(--bg-subtle)] text-xs text-[var(--text-secondary)]">
        Lưu ý: Phiên bản Presenter mới tạo lại sẽ không tự động thay thế phiên bản đang được duyệt cho đến khi Chủ sở hữu kiểm tra QC và xác nhận phê duyệt phiên bản mới.
      </Card>
    </div>
  )
}
