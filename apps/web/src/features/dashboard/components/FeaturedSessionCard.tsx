import { ArrowRight, CalendarPlus, Radio, ShieldAlert } from 'lucide-react'
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

function resolvePresenterThumb(presenterName: string): string {
  const lower = presenterName.toLowerCase()
  if (lower.includes('mai')) return '/demo/presenters/mai.jpg'
  if (lower.includes('an')) return '/demo/presenters/an.jpg'
  if (lower.includes('linh')) return '/demo/presenters/linh.jpg'
  return '/heritage/presenter-heritage.webp'
}

export function FeaturedSessionCard({
  session,
  capabilities,
}: FeaturedSessionCardProps) {
  if (!session) {
    return (
      <Card padding="md" featured className="flex h-full flex-col justify-between gap-4">
        <div className="flex items-start gap-2.5">
          <Radio
            className="mt-0.5 h-5 w-5 shrink-0 text-[var(--accent-gold)]"
            aria-hidden="true"
          />
          <div>
            <h2 className="text-[18px] font-semibold leading-snug text-[var(--text-primary)]">
              Phiên nổi bật
            </h2>
            <p className="mt-0.5 text-xs text-[var(--text-muted)]">
              Theo dõi nhanh trạng thái phiên livestream mới nhất.
            </p>
          </div>
        </div>

        <div className="my-2 flex flex-col items-center rounded-[10px] border border-dashed border-[var(--border-strong)] bg-[var(--bg-subtle)]/60 p-6 text-center">
          <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--bg-surface)] text-[var(--accent-gold)] border border-[var(--border-default)]">
            <Radio className="h-5 w-5" aria-hidden="true" />
          </div>
          <p className="mt-3 text-sm font-semibold text-[var(--text-primary)]">
            Chưa có phiên livestream nào
          </p>
          <p className="mt-1 text-xs text-[var(--text-muted)]">
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
    <Card padding="md" featured className="flex h-full flex-col justify-between gap-4">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Radio
              className="h-5 w-5 shrink-0 text-[var(--accent-gold)]"
              aria-hidden="true"
            />
            <h2 className="text-[18px] font-semibold leading-snug text-[var(--text-primary)]">
              Phiên gần nhất
            </h2>
          </div>
          <StatusBadge
            label={lifecycleBadge.label}
            tone={lifecycleBadge.tone}
            pulse={lifecycleBadge.pulse}
          />
        </div>

        {/* Non-video summary card per Dashboard D5 (ảnh tĩnh chân dung, không subscribe LiveKit hay nút Play giả) */}
        <div className="space-y-3">
          <div className="flex items-start gap-3.5">
            <img
              src={resolvePresenterThumb(session.presenterName)}
              alt={`Ảnh chân dung tĩnh của ${session.presenterName}`}
              className="h-[104px] w-[88px] shrink-0 rounded-[10px] border border-[var(--border-default)] object-cover object-top sm:h-[118px] sm:w-[106px]"
            />

            <div className="min-w-0 flex-1 space-y-1.5">
              <p className="text-xs font-medium text-[var(--text-muted)] tabular-nums">
                {session.code} · {session.skuCount} sản phẩm
              </p>
              <h3 className="text-[15px] font-semibold leading-snug text-[var(--text-primary)]">
                {session.title}
              </h3>

              <div className="space-y-0.5 text-xs text-[var(--text-secondary)]">
                <p className="truncate">
                  Presenter:{' '}
                  <span className="font-medium text-[var(--text-primary)]">
                    {session.presenterName}
                  </span>
                </p>
                {session.activeSkuName ? (
                  <p className="truncate">
                    Đang giới thiệu:{' '}
                    <span className="font-medium text-[var(--text-primary)]">
                      {session.activeSkuName}
                    </span>
                  </p>
                ) : null}
              </div>

              {/* Tách độc lập trạng thái AI & Media; giữ phân cấp rõ ràng theo PO-D03 */}
              <div className="flex flex-wrap gap-1.5 pt-1.5">
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
            </div>
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
