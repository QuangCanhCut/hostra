import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { BarChart3, ChevronRight, FileText, Radio, Search } from 'lucide-react'
import { useScenario } from '@/hooks/useScenario'
import { useSessions } from '@/features/live-session/hooks/useSessions'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Button, ButtonLink } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { formatShortTime } from '@/lib/format'
import { resolveSessionReportStatus } from '@/mocks/m03.store'
import type { BadgeTone } from '@/lib/status-copy'
import type { ReportStatus, SessionLifecycle } from '@/types/domain'

const LIFECYCLE_BADGE: Record<SessionLifecycle, { label: string; tone: BadgeTone }> = {
  CREATED: { label: 'Mới tạo', tone: 'neutral' },
  PREPARING: { label: 'Đang chuẩn bị', tone: 'info' },
  READY: { label: 'Sẵn sàng', tone: 'info' },
  STARTING: { label: 'Đang khởi động', tone: 'warning' },
  LIVE: { label: 'Đang phát LIVE', tone: 'danger' },
  STOPPING: { label: 'Đang dừng', tone: 'warning' },
  STOPPED: { label: 'Đã kết thúc', tone: 'success' },
  FAILED: { label: 'Thất bại', tone: 'danger' },
  CANCELLED: { label: 'Đã hủy', tone: 'neutral' },
}

const REPORT_STATUS_BADGE: Record<ReportStatus, { label: string; tone: BadgeTone }> = {
  READY: { label: 'Báo cáo sẵn sàng', tone: 'success' },
  PARTIAL: { label: 'Dữ liệu một phần', tone: 'warning' },
  PENDING: { label: 'Đang tổng hợp', tone: 'neutral' },
  FAILED: { label: 'Lỗi tổng hợp', tone: 'danger' },
}

export function ReportsHistoryPage() {
  const { role, scenario } = useScenario()
  const { data: sessionsRes, isLoading, isError, refetch } = useSessions()
  const [search, setSearch] = useState('')
  const [lifecycleFilter, setLifecycleFilter] = useState<'ALL' | 'STOPPED' | 'LIVE' | 'OTHER'>('ALL')

  const filtered = useMemo(() => {
    const list = sessionsRes?.items ?? []
    return list.filter((s) => {
      if (role === 'OPERATOR' && !s.assignedOperatorIds.includes('usr-op-01')) return false
      if (lifecycleFilter === 'STOPPED' && s.lifecycle !== 'STOPPED') return false
      if (lifecycleFilter === 'LIVE' && s.lifecycle !== 'LIVE') return false
      if (lifecycleFilter === 'OTHER' && (s.lifecycle === 'STOPPED' || s.lifecycle === 'LIVE')) {
        return false
      }
      if (search.trim()) {
        const q = search.trim().toLowerCase()
        return (
          s.title.toLowerCase().includes(q) ||
          s.code.toLowerCase().includes(q) ||
          s.presenterName.toLowerCase().includes(q)
        )
      }
      return true
    })
  }, [sessionsRes, role, lifecycleFilter, search])

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Báo cáo & Lịch sử phiên livestream
          </h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Theo dõi thời lượng phát thực, lượt vào phòng, câu AI đã phát xác nhận theo Playback ACK
            và xuất báo cáo kiểm toán.
          </p>
        </div>
        <StatusBadge
          tone={role === 'OWNER' ? 'info' : 'neutral'}
          label={
            role === 'OWNER'
              ? 'Chủ sở hữu · Toàn quyền xem & xuất CSV/PDF'
              : 'Vận hành viên · Bản rút gọn các phiên được phân công'
          }
        />
      </div>

      <Card className="p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative flex-1 max-w-md">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Tìm theo mã phiên, tiêu đề hoặc AI Presenter..."
              aria-label="Tìm kiếm báo cáo phiên"
              className="h-10 w-full rounded-[var(--radius-input)] border border-[var(--border-default)] bg-[var(--bg-surface)] pl-9 pr-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--brand-amber)] focus:outline-none"
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {(
              [
                { id: 'ALL', label: 'Tất cả' },
                { id: 'STOPPED', label: 'Đã kết thúc' },
                { id: 'LIVE', label: 'Đang phát LIVE' },
                { id: 'OTHER', label: 'Chưa phát' },
              ] as const
            ).map((f) => (
              <button
                key={f.id}
                type="button"
                onClick={() => setLifecycleFilter(f.id)}
                className={`min-h-9 rounded-full px-3.5 py-1.5 text-xs font-semibold transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)] ${
                  lifecycleFilter === f.id
                    ? 'bg-[var(--brand-navy)] text-white dark:bg-[var(--brand-amber)] dark:text-[var(--brand-navy)]'
                    : 'border border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)]'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-44 rounded-[var(--radius-lg)]" />
          <Skeleton className="h-44 rounded-[var(--radius-lg)]" />
        </div>
      ) : isError ? (
        <EmptyState
          tone="danger"
          icon={<BarChart3 className="h-6 w-6" />}
          title="Không thể tải danh sách báo cáo phiên"
          description="Vui lòng thử tải lại dữ liệu mock."
          action={
            <Button variant="secondary" size="sm" onClick={() => refetch()}>
              Thử lại
            </Button>
          }
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<BarChart3 className="h-6 w-6" />}
          title="Chưa có phiên phù hợp bộ lọc"
          description={
            role === 'OPERATOR'
              ? 'Bạn chỉ nhìn thấy báo cáo của những phiên livestream được Chủ sở hữu phân công.'
              : 'Thử xóa bộ lọc hoặc tạo phiên livestream mới để bắt đầu theo dõi báo cáo.'
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {filtered.map((session) => {
            const lc = LIFECYCLE_BADGE[session.lifecycle]
            const reportStatus: ReportStatus = resolveSessionReportStatus(
              session.id,
              session.lifecycle,
              scenario,
            )
            const rs = REPORT_STATUS_BADGE[reportStatus]
            const exportAvailabilityLabel =
              role !== 'OWNER'
                ? 'Bản rút gọn (chỉ Chủ sở hữu được xuất)'
                : reportStatus === 'READY'
                  ? 'Sẵn sàng xuất CSV / PDF'
                  : reportStatus === 'PARTIAL'
                    ? 'Dữ liệu một phần · Chưa mở xuất file'
                    : reportStatus === 'FAILED'
                      ? 'Lỗi tổng hợp · Không thể xuất'
                      : 'Chưa sẵn sàng xuất (phiên chưa phát)'

            return (
              <Card key={session.id} className="flex flex-col justify-between p-5">
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-mono text-xs font-semibold text-[var(--text-muted)]">
                      {session.code}
                    </span>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <StatusBadge
                        tone={lc.tone}
                        label={lc.label}
                        pulse={session.lifecycle === 'LIVE'}
                      />
                      <StatusBadge tone={rs.tone} label={rs.label} showIcon={false} />
                    </div>
                  </div>

                  <div>
                    <h2 className="text-base font-bold text-[var(--text-primary)]">
                      {session.title}
                    </h2>
                    <p className="mt-1 text-xs text-[var(--text-secondary)]">
                      AI Presenter: <span className="font-medium">{session.presenterName}</span> ·{' '}
                      {session.selectedSkuIds.length} SKU
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-2 rounded-[var(--radius-input)] bg-[var(--bg-subtle)] p-3 text-xs">
                    <div>
                      <span className="text-[var(--text-muted)]">Bắt đầu</span>
                      <p className="mt-0.5 font-semibold text-[var(--text-primary)] tabular-nums">
                        {session.startedAt ? formatShortTime(session.startedAt) : 'Chưa phát'}
                      </p>
                    </div>
                    <div>
                      <span className="text-[var(--text-muted)]">Kết thúc</span>
                      <p className="mt-0.5 font-semibold text-[var(--text-primary)] tabular-nums">
                        {session.stoppedAt
                          ? formatShortTime(session.stoppedAt)
                          : session.lifecycle === 'LIVE'
                            ? 'Đang phát trực tiếp'
                            : '—'}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-[var(--border-default)] pt-3">
                  {session.lifecycle === 'LIVE' ? (
                    <Link
                      to={`/studio/sessions/${session.id}/control`}
                      className="inline-flex min-h-9 items-center gap-1.5 text-xs font-semibold text-[var(--status-danger-fg)] hover:underline"
                    >
                      <Radio className="h-3.5 w-3.5" />
                      Mở phòng điều khiển
                    </Link>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-xs text-[var(--text-muted)]">
                      <FileText className="h-3.5 w-3.5" />
                      {exportAvailabilityLabel}
                    </span>
                  )}

                  <ButtonLink
                    to={`/studio/sessions/${session.id}/report`}
                    variant="secondary"
                    size="sm"
                    rightIcon={<ChevronRight className="h-4 w-4" />}
                  >
                    Xem báo cáo chi tiết
                  </ButtonLink>
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
