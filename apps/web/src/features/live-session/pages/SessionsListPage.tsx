import { Link } from 'react-router-dom'
import { ArrowRight, Plus, Radio } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { useSessions } from '@/features/live-session/hooks/useSessions'
import {
  AI_STATE_COPY,
  MEDIA_HEALTH_COPY,
  SESSION_LIFECYCLE_COPY,
} from '@/lib/status-copy'
import { formatShortTime } from '@/lib/format'

export function SessionsListPage() {
  const { data: auth } = useAuth()
  const { data, isLoading } = useSessions()
  const isOwner = Boolean(auth?.capabilities.canCreateSession)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-52" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  const sessions = data?.items ?? []

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            Phiên livestream
          </h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Quản lý các phiên chuẩn bị, kiểm tra điều kiện sẵn sàng và theo dõi trạng thái phát sóng.
          </p>
        </div>

        {isOwner ? (
          <Link to="/studio/sessions/new">
            <Button variant="primary" leftIcon={<Plus className="h-4 w-4" />}>
              Tạo phiên mới
            </Button>
          </Link>
        ) : null}
      </div>

      {sessions.length === 0 ? (
        <EmptyState
          icon={<Radio className="h-6 w-6" />}
          title="Chưa có phiên livestream nào"
          description={
            isOwner
              ? 'Tạo phiên đầu tiên sau khi bạn đã chuẩn bị AI Presenter và 2–5 sản phẩm OCOP.'
              : 'Bạn chưa được phân công vào phiên livestream nào trong workspace này.'
          }
          action={
            isOwner ? (
              <Link to="/studio/sessions/new">
                <Button variant="primary" leftIcon={<Plus className="h-4 w-4" />}>
                  Tạo phiên mới
                </Button>
              </Link>
            ) : undefined
          }
        />
      ) : (
        <>
          <Card padding="none" className="hidden xl:block overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--border-default)] bg-[var(--bg-subtle)] text-xs font-semibold text-[var(--text-secondary)]">
                    <th className="px-5 py-3">Phiên</th>
                    <th className="px-4 py-3">Trạng thái phát</th>
                    <th className="px-4 py-3">AI & Media / Readiness</th>
                    <th className="px-4 py-3">SKU</th>
                    <th className="px-4 py-3">Cập nhật</th>
                    <th className="px-5 py-3 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-default)]">
                  {sessions.map((s) => {
                    const lc = SESSION_LIFECYCLE_COPY[s.lifecycle]
                    const ai = AI_STATE_COPY[s.aiState]
                    const media = MEDIA_HEALTH_COPY[s.mediaHealth]
                    return (
                      <tr key={s.id} className="hover:bg-[var(--bg-subtle)]/60">
                        <td className="px-5 py-3.5">
                          <p className="font-semibold text-[var(--text-primary)]">
                            {s.code} · {s.title}
                          </p>
                          <p className="text-xs text-[var(--text-muted)]">
                            Presenter: {s.presenterName} ({s.selectedPresenterVersion})
                          </p>
                        </td>
                        <td className="px-4 py-3.5 whitespace-nowrap">
                          <StatusBadge label={lc.label} tone={lc.tone} pulse={lc.pulse} />
                        </td>
                        <td className="px-4 py-3.5">
                          <div className="flex flex-wrap gap-1.5">
                            {s.lifecycle === 'LIVE' ? (
                              <>
                                <StatusBadge label={ai.label} tone={ai.tone} />
                                <StatusBadge label={media.label} tone={media.tone} />
                              </>
                            ) : (
                              <StatusBadge
                                label={
                                  s.readinessOverall === 'READY'
                                    ? 'Đủ điều kiện Start'
                                    : `${s.readinessBlockedCount} điểm chặn Readiness`
                                }
                                tone={s.readinessOverall === 'READY' ? 'success' : 'warning'}
                              />
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3.5 tabular-nums text-xs font-medium text-[var(--text-secondary)]">
                          {s.skuCount} SKU
                        </td>
                        <td className="px-4 py-3.5 tabular-nums text-xs text-[var(--text-muted)]">
                          {formatShortTime(s.updatedAt)}
                        </td>
                        <td className="px-5 py-3.5 text-right whitespace-nowrap">
                          <div className="inline-flex items-center gap-3 text-xs font-semibold">
                            <Link to={`/studio/sessions/${s.id}`} className="hover:underline">
                              Chi tiết
                            </Link>
                            <Link
                              to={`/studio/sessions/${s.id}/readiness`}
                              className="inline-flex items-center gap-1 hover:underline"
                            >
                              Readiness <ArrowRight className="h-3.5 w-3.5" />
                            </Link>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </Card>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:hidden">
            {sessions.map((s) => {
              const lc = SESSION_LIFECYCLE_COPY[s.lifecycle]
              return (
                <Card key={s.id} padding="sm" className="space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-[var(--text-muted)]">
                      {s.code} · {s.skuCount} SKU
                    </span>
                    <StatusBadge label={lc.label} tone={lc.tone} pulse={lc.pulse} />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-[var(--text-primary)]">{s.title}</p>
                    <p className="text-xs text-[var(--text-muted)]">Presenter: {s.presenterName}</p>
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[var(--border-default)] text-xs font-semibold">
                    <Link to={`/studio/sessions/${s.id}/story`} className="hover:underline">
                      Story Planner
                    </Link>
                    <Link
                      to={`/studio/sessions/${s.id}/readiness`}
                      className="inline-flex items-center gap-1 hover:underline"
                    >
                      Readiness <ArrowRight className="h-3.5 w-3.5" />
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
