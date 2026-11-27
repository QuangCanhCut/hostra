import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, ArrowRight, CheckSquare, FileEdit, Settings2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Skeleton } from '@/components/ui/Skeleton'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { useSessionDetail } from '@/features/live-session/hooks/useSessions'
import { SESSION_LIFECYCLE_COPY } from '@/lib/status-copy'

export function SessionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: auth } = useAuth()
  const { data: session, isLoading } = useSessionDetail(id)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (!session) {
    return <Card padding="lg">Không tìm thấy thông tin phiên livestream.</Card>
  }

  const lc = SESSION_LIFECYCLE_COPY[session.lifecycle]
  const isOwner = Boolean(auth?.capabilities.canCreateSession)

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Link
            to="/studio/sessions"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] mb-1"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Quay lại Phiên livestream
          </Link>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="font-display text-[26px] sm:text-[32px] font-bold leading-[1.16] tracking-[-0.02em] text-[var(--text-primary)]">
              {session.code} · {session.title}
            </h1>
            <StatusBadge label={lc.label} tone={lc.tone} pulse={lc.pulse} />
          </div>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">{session.goal}</p>
        </div>

        <div className="flex flex-wrap gap-2">
          {isOwner ? (
            <Link to={`/studio/sessions/${session.id}/setup`}>
              <Button variant="secondary" size="sm" leftIcon={<Settings2 className="h-4 w-4" />}>
                Sửa cấu hình & SKU
              </Button>
            </Link>
          ) : null}
          <Link to={`/studio/sessions/${session.id}/readiness`}>
            <Button variant="primary" size="sm" leftIcon={<CheckSquare className="h-4 w-4" />}>
              Kiểm tra Readiness
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        <Card padding="md" className="space-y-2">
          <p className="text-xs font-semibold text-[var(--text-muted)]">AI Presenter đã gắn</p>
          <p className="text-base font-bold">{session.presenterName}</p>
          <p className="text-xs text-[var(--text-secondary)]">
            Phiên bản chọn: {session.selectedPresenterVersion}
          </p>
          <Link
            to={`/studio/presenters/${session.presenterId}`}
            className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--text-primary)] hover:underline pt-1"
          >
            Mở Presenter <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </Card>

        <Card padding="md" className="space-y-2">
          <p className="text-xs font-semibold text-[var(--text-muted)]">Kịch bản Story Plan</p>
          <p className="text-base font-bold">
            {session.storyApprovalStatus === 'APPROVED' ? 'Đã phê duyệt' : 'Chờ rà soát / duyệt'}
          </p>
          <p className="text-xs text-[var(--text-secondary)]">
            Số SKU trong phiên: {session.skuCount} · Dự kiến {session.estimatedMinutes} phút
          </p>
          <Link
            to={`/studio/sessions/${session.id}/story`}
            className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--text-primary)] hover:underline pt-1"
          >
            <FileEdit className="h-3.5 w-3.5" /> Mở Story Planner
          </Link>
        </Card>

        <Card padding="md" className="space-y-2">
          <p className="text-xs font-semibold text-[var(--text-muted)]">Điều kiện khởi chạy (Readiness)</p>
          <p className="text-base font-bold">
            {session.readinessOverall === 'READY'
              ? 'Tất cả điều kiện đã đạt'
              : `${session.readinessBlockedCount} điều kiện chưa đạt`}
          </p>
          <p className="text-xs text-[var(--text-secondary)]">
            Revision phiên: v{session.revision} · Epoch {session.epoch}
          </p>
          <Link
            to={`/studio/sessions/${session.id}/readiness`}
            className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--text-primary)] hover:underline pt-1"
          >
            Xem danh sách cổng kiểm tra <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </Card>
      </div>
    </div>
  )
}
