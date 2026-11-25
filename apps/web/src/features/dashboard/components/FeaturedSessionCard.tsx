import { ArrowRight, CalendarPlus, Radio, ShieldAlert, Sparkles } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { ButtonLink } from '@/components/ui/Button'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  AI_STATE_COPY,
  MEDIA_HEALTH_COPY,
  SESSION_LIFECYCLE_COPY,
} from '@/lib/status-copy'
import type { SessionSummary } from '@/types/domain'
import type { UserCapabilities } from '@/types/auth'

export interface FeaturedSessionCardProps {
  session: SessionSummary | null
  capabilities?: UserCapabilities
}

export function FeaturedSessionCard({
  session,
  capabilities,
}: FeaturedSessionCardProps) {
  if (!session) {
    return (
      <Card padding="md" className="flex h-full flex-col justify-between">
        <div>
          <h2 className="text-base font-bold text-[var(--text-primary)]">
            Phiên nổi bật
          </h2>
          <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
            Theo dõi nhanh trạng thái phiên livestream mới nhất
          </p>
        </div>

        <div className="my-5 flex flex-col items-center rounded-[10px] border border-dashed border-[var(--border-strong)] bg-[var(--bg-subtle)] p-6 text-center">
          <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--bg-surface)] text-[var(--text-secondary)]">
            <Radio className="h-5 w-5" aria-hidden="true" />
          </div>
          <p className="mt-3 text-sm font-semibold text-[var(--text-primary)]">
            Chưa có phiên livestream nào
          </p>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">
            {capabilities?.canCreateSession
              ? 'Sau khi có AI Presenter và 2–5 sản phẩm OCOP, bạn có thể tạo phiên mới.'
              : 'Bạn chưa được phân công vào phiên livestream nào trong workspace này.'}
          </p>
        </div>

        {capabilities?.canCreateSession ? (
          <ButtonLink
            to="/studio/sessions/new"
            variant="primary"
            className="w-full"
            leftIcon={<CalendarPlus className="h-4 w-4" />}
          >
            Tạo phiên livestream mới
          </ButtonLink>
        ) : (
          <ButtonLink to="/studio/sessions" variant="secondary" className="w-full">
            Xem danh sách phiên
          </ButtonLink>
        )}
      </Card>
    )
  }

  const lifecycleBadge = SESSION_LIFECYCLE_COPY[session.lifecycle]
  const aiBadge = AI_STATE_COPY[session.aiState]
  const mediaBadge = MEDIA_HEALTH_COPY[session.mediaHealth]

  const isLiveOrStarting =
    session.lifecycle === 'LIVE' || session.lifecycle === 'STARTING'
  const isStopped = session.lifecycle === 'STOPPED'

  const cta = isLiveOrStarting
    ? {
        label: 'Mở phòng điều khiển',
        to: `/studio/sessions/${session.id}/control`,
      }
    : isStopped
      ? {
          label: 'Xem báo cáo phiên',
          to: `/studio/sessions/${session.id}/report`,
        }
      : capabilities?.canStartSession
        ? {
            label: 'Kiểm tra sẵn sàng',
            to: `/studio/sessions/${session.id}/readiness`,
          }
        : {
            label: 'Xem chi tiết phiên',
            to: `/studio/sessions/${session.id}/readiness`,
          }

  return (
    <Card padding="md" className="flex h-full flex-col justify-between gap-4">
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-base font-bold text-[var(--text-primary)]">
            Phiên gần nhất
          </h2>
          <StatusBadge
            label={lifecycleBadge.label}
            tone={lifecycleBadge.tone}
            pulse={lifecycleBadge.pulse}
          />
        </div>

        {/* Non-video summary card per Dashboard D5 (No Video Preview / No LiveKit subscribe on Dashboard) */}
        <div className="rounded-[10px] border border-[var(--border-default)] bg-[var(--bg-subtle)] p-4 space-y-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs font-semibold text-[var(--text-muted)]">
                {session.code} · {session.skuCount} sản phẩm
              </p>
              <h3 className="mt-0.5 text-sm font-bold text-[var(--text-primary)]">
                {session.title}
              </h3>
            </div>
            <div
              aria-hidden="true"
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[10px] bg-[var(--brand-navy)] text-[var(--brand-amber)]"
            >
              <Sparkles className="h-5 w-5" />
            </div>
          </div>

          <div className="text-xs text-[var(--text-secondary)] space-y-1">
            <p>
              Presenter: <span className="font-medium text-[var(--text-primary)]">{session.presenterName}</span>
            </p>
            {session.activeSkuName ? (
              <p>
                Đang giới thiệu:{' '}
                <span className="font-medium text-[var(--text-primary)]">
                  {session.activeSkuName}
                </span>
              </p>
            ) : null}
          </div>

          {/* Tách độc lập trạng thái AI & Media; dùng dạng nhẹ (subtle) khi hoạt động bình thường (PO-D03) */}
          <div className="flex flex-wrap gap-2 pt-1">
            <StatusBadge
              label={aiBadge.label}
              tone={aiBadge.tone}
              subtle={session.aiState === 'ACTIVE'}
            />
            <StatusBadge
              label={mediaBadge.label}
              tone={mediaBadge.tone}
              subtle={session.mediaHealth === 'HEALTHY'}
            />
          </div>

          {session.fallbackDescription ? (
            <div className="flex items-start gap-2 rounded-[8px] border border-[var(--status-warning-border)] bg-[var(--status-warning-bg)] px-3 py-2 text-xs text-[var(--status-warning-fg)]">
              <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              <span>{session.fallbackDescription}</span>
            </div>
          ) : null}
        </div>
      </div>

      <ButtonLink
        to={cta.to}
        variant="primary"
        size="md"
        className="w-full"
        rightIcon={<ArrowRight className="h-4 w-4" />}
      >
        {cta.label}
      </ButtonLink>
    </Card>
  )
}
