import { Link } from 'react-router-dom'
import { ArrowRight, Calendar } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import {
  DataTable,
  TABLE_BODY_CLASS,
  TABLE_HEAD_ROW_CLASS,
  TABLE_ROW_HOVER_CLASS,
} from '@/components/ui/DataTable'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatShortTime } from '@/lib/format'
import {
  AI_STATE_COPY,
  MEDIA_HEALTH_COPY,
  SESSION_LIFECYCLE_COPY,
} from '@/lib/status-copy'
import type { SessionSummary } from '@/types/domain'

function resolveSessionRoute(session: SessionSummary): string {
  if (session.lifecycle === 'LIVE' || session.lifecycle === 'STARTING') {
    return `/studio/sessions/${session.id}/control`
  }
  if (session.lifecycle === 'STOPPED') {
    return `/studio/sessions/${session.id}/report`
  }
  return `/studio/sessions/${session.id}/readiness`
}

function resolveSessionActionLabel(session: SessionSummary): string {
  if (session.lifecycle === 'LIVE' || session.lifecycle === 'STARTING') {
    return 'Phòng điều khiển'
  }
  if (session.lifecycle === 'STOPPED') {
    return 'Xem báo cáo'
  }
  return 'Tiếp tục chuẩn bị'
}

export function RecentSessionsSection({
  sessions,
}: {
  sessions: SessionSummary[]
}) {
  const visible = sessions.slice(0, 3)

  return (
    <section aria-label="Phiên livestream gần đây" className="space-y-3.5">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-display text-[21px] font-bold leading-snug text-[var(--text-primary)] sm:text-[23px]">
          Phiên livestream gần đây
        </h2>
        <Link
          to="/studio/sessions"
          className="inline-flex min-h-9 shrink-0 items-center gap-1 whitespace-nowrap rounded-[8px] px-2.5 py-1.5 text-xs font-semibold text-[var(--accent-gold)] hover:bg-[var(--bg-subtle)]"
        >
          <span>Xem tất cả</span>
          <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
        </Link>
      </div>

      {visible.length === 0 ? (
        <Card padding="md" className="py-8 text-center">
          <p className="text-sm font-medium text-[var(--text-primary)]">
            Chưa có lịch sử phiên livestream
          </p>
          <p className="mt-1 text-xs text-[var(--text-muted)]">
            Các phiên bạn tạo hoặc được phân công vận hành sẽ hiển thị tại đây.
          </p>
        </Card>
      ) : (
        <>
          {/* Wide Desktop (>= 1280px): Full semantic table */}
          <DataTable className="hidden xl:block">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className={TABLE_HEAD_ROW_CLASS}>
                  <th className="px-5 py-3.5">Phiên</th>
                  <th className="px-4 py-3.5">Trạng thái phát</th>
                  <th className="px-4 py-3.5">AI &amp; Media</th>
                  <th className="px-4 py-3.5">Sản phẩm</th>
                  <th className="px-4 py-3.5">Cập nhật</th>
                  <th className="px-5 py-3.5 text-right">Thao tác</th>
                </tr>
              </thead>
              <tbody className={TABLE_BODY_CLASS}>
                {visible.map((session) => {
                  const lifecycle = SESSION_LIFECYCLE_COPY[session.lifecycle]
                  const ai = AI_STATE_COPY[session.aiState]
                  const media = MEDIA_HEALTH_COPY[session.mediaHealth]
                  return (
                    <tr key={session.id} className={TABLE_ROW_HOVER_CLASS}>
                      <td className="px-5 py-3.5">
                        <p className="font-semibold text-[var(--text-primary)]">
                          {session.code} · {session.title}
                        </p>
                        <p className="mt-0.5 text-xs text-[var(--text-muted)]">
                          Presenter: {session.presenterName}
                        </p>
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <StatusBadge
                          label={lifecycle.label}
                          tone={lifecycle.tone}
                          pulse={lifecycle.pulse}
                          className="whitespace-nowrap"
                        />
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="flex flex-wrap gap-1.5">
                          {session.lifecycle === 'LIVE' ? (
                            <>
                              <StatusBadge
                                label={ai.label}
                                tone={ai.tone}
                                subtle={session.aiState === 'ACTIVE'}
                                className="whitespace-nowrap"
                              />
                              <StatusBadge
                                label={media.label}
                                tone={media.tone}
                                subtle={session.mediaHealth === 'HEALTHY'}
                                className="whitespace-nowrap"
                              />
                            </>
                          ) : (
                            <span className="text-xs text-[var(--text-muted)]">—</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap tabular-nums text-xs font-medium text-[var(--text-secondary)]">
                        {session.skuCount} SKU
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap tabular-nums text-xs text-[var(--text-muted)]">
                        {formatShortTime(session.updatedAt)}
                      </td>
                      <td className="px-5 py-3.5 text-right whitespace-nowrap">
                        <Link
                          to={resolveSessionRoute(session)}
                          className="inline-flex min-h-9 items-center gap-1.5 rounded-[8px] border border-[var(--border-strong)] px-3 py-1.5 text-xs font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-raised)] hover:border-[var(--accent-gold)]"
                        >
                          <span>{resolveSessionActionLabel(session)}</span>
                          <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                        </Link>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </DataTable>

          {/* Tablet & Mobile (< 1280px): Responsive cards preserving all business metadata */}
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:hidden">
            {visible.map((session) => {
              const lifecycle = SESSION_LIFECYCLE_COPY[session.lifecycle]
              const ai = AI_STATE_COPY[session.aiState]
              const media = MEDIA_HEALTH_COPY[session.mediaHealth]
              return (
                <Card key={session.id} padding="sm" className="flex flex-col justify-between gap-3">
                  <div className="space-y-2.5">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs font-semibold text-[var(--text-muted)] tabular-nums">
                        {session.code} · {session.skuCount} SKU
                      </span>
                      <StatusBadge
                        label={lifecycle.label}
                        tone={lifecycle.tone}
                        pulse={lifecycle.pulse}
                        className="whitespace-nowrap"
                      />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-[var(--text-primary)] leading-snug">
                        {session.title}
                      </p>
                      <p className="mt-0.5 text-xs text-[var(--text-muted)]">
                        Presenter: {session.presenterName}
                      </p>
                    </div>
                    {session.lifecycle === 'LIVE' ? (
                      <div className="flex flex-wrap gap-1.5">
                        <StatusBadge
                          label={ai.label}
                          tone={ai.tone}
                          subtle={session.aiState === 'ACTIVE'}
                          className="whitespace-nowrap"
                        />
                        <StatusBadge
                          label={media.label}
                          tone={media.tone}
                          subtle={session.mediaHealth === 'HEALTHY'}
                          className="whitespace-nowrap"
                        />
                      </div>
                    ) : null}
                  </div>
                  <div className="flex items-center justify-between text-xs text-[var(--text-muted)] pt-2.5 border-t border-[var(--border-default)]">
                    <span className="inline-flex items-center gap-1 tabular-nums">
                      <Calendar className="h-3.5 w-3.5" aria-hidden="true" />
                      {formatShortTime(session.updatedAt)}
                    </span>
                    <Link
                      to={resolveSessionRoute(session)}
                      className="inline-flex min-h-9 items-center gap-1 rounded-[8px] border border-[var(--border-strong)] px-2.5 py-1.5 font-semibold text-[var(--text-primary)] hover:bg-[var(--bg-raised)]"
                    >
                      <span>{resolveSessionActionLabel(session)}</span>
                      <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                    </Link>
                  </div>
                </Card>
              )
            })}
          </div>
        </>
      )}
    </section>
  )
}
