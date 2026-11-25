import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Clock,
  Play,
  RefreshCw,
  ShieldAlert,
  XCircle,
} from 'lucide-react'
import { Button, ButtonLink } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Banner } from '@/components/ui/Banner'
import { Modal } from '@/components/ui/Modal'
import { Skeleton } from '@/components/ui/Skeleton'
import { useAuth } from '@/features/auth/hooks/useAuth'
import {
  useReadiness,
  useStartSession,
} from '@/features/live-session/hooks/useSessions'
import { SESSION_LIFECYCLE_COPY } from '@/lib/status-copy'
import type { StartCommandResult } from '@/types/m02'

export function ReadinessPage() {
  const { id } = useParams<{ id: string }>()
  const sessionId = id ?? 'ses-015'
  const { data: auth } = useAuth()
  const { data: readiness, isLoading, isFetching, refetch } = useReadiness(sessionId)
  const startMutation = useStartSession(sessionId)

  const [confirmOpen, setConfirmOpen] = useState(false)
  const [commandResult, setCommandResult] = useState<StartCommandResult | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const canStartRole = Boolean(auth?.capabilities.canStartSession)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (!readiness) {
    return <Card padding="lg">Không tìm thấy thông tin Readiness của phiên này.</Card>
  }

  const lc = SESSION_LIFECYCLE_COPY[readiness.sessionLifecycle]
  const canClickStart =
    canStartRole &&
    readiness.overallReady &&
    readiness.sessionLifecycle !== 'LIVE' &&
    readiness.sessionLifecycle !== 'STARTING'

  const handleRequestStart = async () => {
    setConfirmOpen(false)
    setErrorMsg(null)
    try {
      const res = await startMutation.mutateAsync('REQUEST')
      setCommandResult(res)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Lệnh START bị từ chối.')
    }
  }

  const handleConfirmMediaLive = async () => {
    setErrorMsg(null)
    try {
      const res = await startMutation.mutateAsync('CONFIRM_MEDIA')
      setCommandResult(res)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Không thể xác nhận LIVE.')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Link
            to={`/studio/sessions/${sessionId}`}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] mb-1"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Quay lại {readiness.sessionCode}
          </Link>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">
              Kiểm tra sẵn sàng · {readiness.sessionCode}
            </h1>
            <StatusBadge label={lc.label} tone={lc.tone} pulse={lc.pulse} />
          </div>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            {readiness.sessionTitle} · Toàn bộ cổng kiểm tra độc lập phải Đạt trước khi Chủ sở hữu khởi chạy phiên.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            loading={isFetching}
            leftIcon={<RefreshCw className="h-4 w-4" />}
            onClick={() => refetch()}
          >
            Kiểm tra lại
          </Button>

          {canStartRole ? (
            <Button
              variant="primary"
              size="md"
              disabled={!canClickStart}
              loading={startMutation.isPending}
              leftIcon={<Play className="h-4 w-4" />}
              onClick={() => setConfirmOpen(true)}
            >
              Bắt đầu livestream
            </Button>
          ) : (
            <StatusBadge label="Chỉ Chủ sở hữu được Bắt đầu" tone="neutral" />
          )}
        </div>
      </div>

      {!readiness.overallReady ? (
        <Banner
          severity="warning"
          title={`Chưa thể khởi chạy (${readiness.blockedCount} bị chặn · ${readiness.pendingCount} đang chờ)`}
          description="Hệ thống tính Readiness từ tất cả các cổng độc lập (Rights, Presenter QC, 2–5 SKU, OCOP, Knowledge, Story, Media). Hãy xử lý từng mục bên dưới."
        />
      ) : (
        <Banner
          severity="info"
          title="Toàn bộ điều kiện Readiness đã ĐẠT"
          description={
            canStartRole
              ? 'Bạn có thể gửi yêu cầu Bắt đầu livestream (mô phỏng vòng đời ACCEPTED → STARTING → LIVE).'
              : 'Phiên đã sẵn sàng. Vui lòng chờ Chủ sở hữu thực hiện lệnh Bắt đầu livestream.'
          }
        />
      )}

      {errorMsg ? <Banner severity="danger" title="Lệnh START bị từ chối" description={errorMsg} /> : null}

      {commandResult ? (
        <Card padding="md" className="border-[var(--brand-amber)] bg-[var(--bg-hero)] space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-[var(--text-primary)]" />
              <p className="text-sm font-bold text-[var(--text-primary)]">
                Trạng thái lệnh START (Môi trường mô phỏng — không phát livestream thật)
              </p>
            </div>
            <StatusBadge
              label={
                commandResult.status === 'APPLIED'
                  ? 'APPLIED · Đang LIVE'
                  : commandResult.status === 'ACCEPTED'
                    ? 'ACCEPTED · Đang khởi chạy (Chưa LIVE)'
                    : 'Bị từ chối'
              }
              tone={
                commandResult.status === 'APPLIED'
                  ? 'success'
                  : commandResult.status === 'ACCEPTED'
                    ? 'info'
                    : 'danger'
              }
            />
          </div>
          <p className="text-xs text-[var(--text-secondary)]">{commandResult.reason}</p>
          {commandResult.status === 'ACCEPTED' && canStartRole ? (
            <div className="flex flex-wrap gap-2">
              <Button
                variant="primary"
                size="sm"
                loading={startMutation.isPending}
                onClick={handleConfirmMediaLive}
              >
                Mô phỏng Media xác nhận đã LIVE (APPLIED)
              </Button>
            </div>
          ) : null}
        </Card>
      ) : null}

      {/* Ưu tiên đưa các mục Bị chặn / Đang chờ lên đầu danh sách để chủ shop xử lý ngay */}
      <Card padding="none" className="overflow-hidden">
        <ul className="divide-y divide-[var(--border-default)]">
          {[...readiness.gates]
            .sort((a, b) => {
              const order = { BLOCKED: 0, PENDING: 1, PASS: 2 } as const
              return order[a.status] - order[b.status]
            })
            .map((gate) => {
            const Icon =
              gate.status === 'PASS'
                ? CheckCircle2
                : gate.status === 'PENDING'
                  ? Clock
                  : XCircle
            const iconColor =
              gate.status === 'PASS'
                ? 'text-[var(--status-success-fg)]'
                : gate.status === 'PENDING'
                  ? 'text-[var(--status-warning-fg)]'
                  : 'text-[var(--status-danger-fg)]'

            return (
              <li
                key={gate.id}
                className={`flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between ${
                  gate.status === 'BLOCKED'
                    ? 'bg-[var(--status-danger-bg)]/25'
                    : gate.status === 'PENDING'
                      ? 'bg-[var(--status-warning-bg)]/25'
                      : ''
                }`}
              >
                <div className="flex items-start gap-3">
                  <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${iconColor}`} aria-hidden="true" />
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-bold text-[var(--text-primary)]">{gate.label}</p>
                      <StatusBadge
                        label={
                          gate.status === 'PASS'
                            ? 'Đạt'
                            : gate.status === 'PENDING'
                              ? 'Đang chờ'
                              : 'Bị chặn'
                        }
                        tone={
                          gate.status === 'PASS'
                            ? 'success'
                            : gate.status === 'PENDING'
                              ? 'warning'
                              : 'danger'
                        }
                      />
                    </div>
                    <p className="text-xs text-[var(--text-secondary)]">{gate.reason}</p>
                    <p className="text-[11px] text-[var(--text-muted)]">Nguồn kiểm tra: {gate.sourceLabel}</p>
                  </div>
                </div>

                {gate.remediationRoute && gate.remediationLabel ? (
                  <ButtonLink
                    to={gate.remediationRoute}
                    variant={gate.status === 'PASS' ? 'ghost' : 'secondary'}
                    size="sm"
                    rightIcon={<ArrowRight className="h-3.5 w-3.5" />}
                    className="shrink-0"
                  >
                    {gate.remediationLabel}
                  </ButtonLink>
                ) : null}
              </li>
            )
          })}
        </ul>
      </Card>

      <Modal
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title="Xác nhận gửi yêu cầu khởi chạy livestream?"
        description="Lệnh START sẽ chuyển phiên sang trạng thái Đang khởi chạy (STARTING) và chỉ chuyển LIVE sau khi bộ phát media xác nhận."
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmOpen(false)}>
              Hủy
            </Button>
            <Button variant="primary" onClick={handleRequestStart}>
              Xác nhận gửi lệnh START
            </Button>
          </>
        }
      >
        <p className="text-sm text-[var(--text-secondary)]">
          Phiên <span className="font-semibold text-[var(--text-primary)]">{readiness.sessionCode}</span> đang ở phiên bản kiểm tra v{readiness.revision}. Đây là luồng mô phỏng phục vụ kiểm thử Milestone 2.
        </p>
      </Modal>
    </div>
  )
}
