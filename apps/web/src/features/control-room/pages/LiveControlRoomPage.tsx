import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  Activity,
  AlertOctagon,
  ArrowLeftRight,
  ChevronDown,
  ChevronUp,
  Copy,
  History,
  Pause,
  Play,
  RefreshCw,
  ShieldAlert,
  SkipForward,
  Square,
  Stethoscope,
  WifiOff,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Banner } from '@/components/ui/Banner'
import { Modal } from '@/components/ui/Modal'
import { Drawer } from '@/components/ui/Drawer'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { PresenterPortrait, ProductThumb } from '@/components/shared/PortraitAvatar'
import {
  useAdvanceSpeech,
  useControlCommand,
  useControlRoom,
  useSimulateControlEvent,
} from '@/features/control-room/hooks/useControlRoom'
import {
  AI_STATE_COPY,
  MEDIA_HEALTH_COPY,
  SESSION_LIFECYCLE_COPY,
} from '@/lib/status-copy'
import { formatShortTime, formatVnd } from '@/lib/format'
import { ApiError } from '@/services/api-client'
import { cn } from '@/lib/cn'

const SPEECH_PHASE_LABELS: Record<string, string> = {
  PLANNING: 'Đang lập ý',
  VERIFYING: 'Đang kiểm chứng nguồn',
  PREPARING_AUDIO: 'Đang tạo giọng nói',
  LIP_SYNC: 'Đang đồng bộ khẩu hình',
  READY: 'Dự kiến · Chưa phát',
  COMMITTED: 'Đã chốt phát',
  PLAYING: 'Đang phát sóng',
  PLAYBACK_COMPLETED: 'Đã phát xong (Playback ACK)',
  CANCELLED: 'Đã hủy',
}

export function LiveControlRoomPage() {
  const { id } = useParams<{ id: string }>()
  const sessionId = id ?? 'ses-014'

  const { data: snap, isLoading, isError, error, refetch } = useControlRoom(sessionId)
  const cmdMutation = useControlCommand(sessionId)
  const advanceSpeechMutation = useAdvanceSpeech(sessionId)
  const simEventMutation = useSimulateControlEvent(sessionId)

  const [mobileTab, setMobileTab] = useState<'comments' | 'queue'>('comments')
  const [aiExpanded, setAiExpanded] = useState(true)
  const [switchDrawerOpen, setSwitchDrawerOpen] = useState(false)
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(false)
  const [activityLogOpen, setActivityLogOpen] = useState(false)
  const [stopModalOpen, setStopModalOpen] = useState(false)
  const [emergencyModalOpen, setEmergencyModalOpen] = useState(false)
  const [selectedTargetSkuId, setSelectedTargetSkuId] = useState<string>('')
  const [toastMsg, setToastMsg] = useState<{ tone: 'info' | 'danger'; text: string } | null>(null)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12 w-full" />
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
          <Skeleton className="h-96 lg:col-span-7" />
          <Skeleton className="h-96 lg:col-span-5" />
        </div>
      </div>
    )
  }

  if (isError || !snap) {
    const isForbidden = error instanceof ApiError && error.status === 403
    return (
      <EmptyState
        tone={isForbidden ? 'warning' : 'danger'}
        icon={<ShieldAlert className="h-6 w-6" />}
        title={
          isForbidden
            ? 'Bạn không có quyền truy cập Phòng điều khiển phiên này'
            : 'Không thể tải trạng thái Phòng điều khiển'
        }
        description={
          error instanceof Error ? error.message : 'Vui lòng thử đồng bộ lại snapshot.'
        }
        action={
          <Link to="/studio/sessions">
            <Button variant="secondary">Quay lại Danh sách phiên</Button>
          </Link>
        }
      />
    )
  }

  const lifecycleCopy = SESSION_LIFECYCLE_COPY[snap.lifecycle]
  const aiCopy = AI_STATE_COPY[snap.aiState]
  const mediaCopy = MEDIA_HEALTH_COPY[snap.mediaHealth]
  const isStale = snap.connectionFreshness !== 'CONNECTED'
  const isStopped = snap.lifecycle === 'STOPPED'
  const controlsDisabled = !snap.canOperate || isStale || isStopped

  const runCommand = async (
    type:
      | 'PAUSE_AI'
      | 'RESUME_AI'
      | 'SWITCH_SKU'
      | 'PRIORITIZE_COMMENT'
      | 'SKIP_PENDING'
      | 'STOP'
      | 'EMERGENCY_STOP',
    extra?: {
      targetSkuId?: string
      commentId?: string
      simulatePhase?: 'ACCEPT_ONLY' | 'APPLY'
      overrideRevision?: number
    },
  ) => {
    setToastMsg(null)
    try {
      const res = await cmdMutation.mutateAsync({
        type,
        expectedRevision: extra?.overrideRevision ?? snap.revision,
        targetSkuId: extra?.targetSkuId,
        commentId: extra?.commentId,
        simulatePhase: extra?.simulatePhase,
      })
      setToastMsg({
        tone: res.command.status === 'REJECTED' ? 'danger' : 'info',
        text: `${res.command.actorName}: ${res.command.reason}`,
      })
    } catch (err) {
      setToastMsg({
        tone: 'danger',
        text: err instanceof Error ? err.message : 'Lệnh bị từ chối hoặc xung đột revision.',
      })
      refetch()
    }
  }

  const handleCopyInvite = async () => {
    if (!snap.activeInviteUrl) return
    const full = `${window.location.origin}${snap.activeInviteUrl}`
    try {
      await navigator.clipboard.writeText(full)
    } catch {
      // ignore clipboard error in headless tests
    }
    setToastMsg({ tone: 'info', text: `Đã sao chép đường dẫn mời xem: ${full}` })
  }

  const queuedComments = snap.comments.filter(
    (c) => c.queueStatus === 'QUEUED' || c.queueStatus === 'PRIORITIZED',
  )

  return (
    <div className="space-y-4 pb-24">
      {/* Z01 & Z02: Header + Compact 5-Axis Status Bar (CR-D4=A) */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)] sm:text-2xl">
            Phòng điều khiển livestream · {snap.sessionCode}
          </h1>
          <p className="text-xs text-[var(--text-secondary)]">
            {snap.sessionTitle} · Revision v{snap.revision} · Epoch {snap.epoch} · Môi trường mô phỏng
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {snap.canCopyInvite ? (
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<Copy className="h-3.5 w-3.5" />}
              onClick={handleCopyInvite}
            >
              Sao chép link mời
            </Button>
          ) : null}
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<History className="h-3.5 w-3.5" />}
            onClick={() => setActivityLogOpen(true)}
          >
            Nhật ký lệnh ({snap.commands.length})
          </Button>
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<Stethoscope className="h-3.5 w-3.5" />}
            onClick={() => setDiagnosticsOpen(true)}
          >
            Chẩn đoán
          </Button>
          {/* Emergency Stop separated from normal runtime actions (CR-D3 & CR-D11=B) */}
          <Button
            variant="destructive"
            size="sm"
            disabled={!snap.canOperate || isStopped}
            leftIcon={<AlertOctagon className="h-4 w-4" />}
            onClick={() => setEmergencyModalOpen(true)}
          >
            Dừng khẩn cấp
          </Button>
        </div>
      </div>

      {/* Independent 5-axis status bar */}
      <Card padding="sm" className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge label={lifecycleCopy.label} tone={lifecycleCopy.tone} pulse={lifecycleCopy.pulse} />
          <StatusBadge label={aiCopy.label} tone={aiCopy.tone} />
          <StatusBadge label={mediaCopy.label} tone={mediaCopy.tone} />
          <StatusBadge
            label={
              snap.publisherState === 'CONNECTED'
                ? 'Publisher ổn định'
                : snap.publisherState === 'DEGRADED'
                  ? 'Publisher suy giảm'
                  : 'Publisher đã ngắt'
            }
            tone={
              snap.publisherState === 'CONNECTED'
                ? 'success'
                : snap.publisherState === 'DEGRADED'
                  ? 'warning'
                  : 'neutral'
            }
          />
          <StatusBadge
            label={isStale ? 'Dữ liệu có thể cũ' : 'Đồng bộ realtime'}
            tone={isStale ? 'warning' : 'info'}
          />
        </div>

        {/* Compact Mock Simulation Controls for QA */}
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            onClick={() => simEventMutation.mutate('TOGGLE_DEGRADED')}
            className="rounded-[6px] border border-[var(--border-default)] px-2 py-1 text-[11px] font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] cursor-pointer"
          >
            Mô phỏng Media suy giảm
          </button>
          <button
            type="button"
            onClick={() => simEventMutation.mutate('TOGGLE_STALE')}
            className="rounded-[6px] border border-[var(--border-default)] px-2 py-1 text-[11px] font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] cursor-pointer"
          >
            Mô phỏng mất kết nối
          </button>
          <button
            type="button"
            onClick={() =>
              runCommand('PAUSE_AI', { overrideRevision: Math.max(1, snap.revision - 1) })
            }
            className="rounded-[6px] border border-[var(--border-default)] px-2 py-1 text-[11px] font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] cursor-pointer"
          >
            Mô phỏng xung đột 409
          </button>
        </div>
      </Card>

      {/* Conditional Banners (Media DEGRADED, Stale, Toast) */}
      {snap.mediaHealth === 'DEGRADED' ? (
        <Banner
          severity="warning"
          title="Chất lượng hình ảnh đang giảm — Luồng live vẫn hoạt động"
          description={
            snap.fallbackModeLabel ||
            'Hệ thống đang dùng cảnh sản phẩm dự phòng + âm thanh đã xác minh. Không đồng nghĩa phiên đã dừng.'
          }
          action={
            <Button variant="secondary" size="sm" onClick={() => setDiagnosticsOpen(true)}>
              Mở chẩn đoán
            </Button>
          }
        />
      ) : null}

      {isStale ? (
        <Banner
          severity="danger"
          title="Kết nối dữ liệu đang gián đoạn — Trạng thái có thể đã cũ"
          description="Các thao tác rủi ro tạm bị khóa để tránh gửi lệnh trùng. Hãy đồng bộ lại snapshot mới nhất."
          action={
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
              onClick={() => simEventMutation.mutate('TOGGLE_STALE')}
            >
              Kết nối lại & Đồng bộ
            </Button>
          }
        />
      ) : null}

      {toastMsg ? (
        <Banner
          severity={toastMsg.tone === 'danger' ? 'danger' : 'info'}
          title={toastMsg.tone === 'danger' ? 'Kết quả lệnh / Xung đột' : 'Thông báo vận hành'}
          description={toastMsg.text}
        />
      ) : null}

      {/* Main 2-Column Workspace (CR-D1=A: Left 60% Video/Product, Right 40% Comments/Queue/AI) */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
        {/* Left Column (60%) */}
        <div className="lg:col-span-7 space-y-4">
          <Card padding="none" className="overflow-hidden">
            <div className="relative aspect-video w-full bg-[#0B1322]">
              {snap.mediaHealth === 'DEGRADED' ? (
                <div className="flex h-full w-full flex-col items-center justify-center gap-3 p-6 text-center text-white">
                  <ProductThumb
                    skuId={snap.activeSkuId}
                    name={snap.activeSkuName}
                    className="h-24 w-24"
                  />
                  <div className="space-y-1">
                    <StatusBadge label="Cảnh sản phẩm dự phòng · Âm thanh xác minh" tone="warning" />
                    <p className="text-sm font-bold">{snap.activeSkuName}</p>
                    <p className="text-xs text-slate-300">
                      {formatVnd(snap.activeSkuPriceVnd)} · Luồng phát vẫn duy trì liên tục
                    </p>
                  </div>
                </div>
              ) : (
                <div className="relative h-full w-full">
                  <PresenterPortrait
                    presenterId={snap.presenterId}
                    name={snap.presenterName}
                    className="h-full w-full aspect-video rounded-none border-0"
                  />
                  <div className="absolute top-3 left-3 flex flex-wrap items-center gap-2">
                    <StatusBadge
                      label={lifecycleCopy.label}
                      tone={lifecycleCopy.tone}
                      pulse={lifecycleCopy.pulse}
                    />
                    <span className="rounded-full bg-slate-900/80 px-2.5 py-0.5 text-[11px] font-medium text-white">
                      Môi trường mô phỏng (Không phát LiveKit thật)
                    </span>
                  </div>
                  {snap.aiState === 'PAUSED' ? (
                    <div className="absolute inset-0 flex items-center justify-center bg-slate-950/55 p-4 text-center">
                      <div className="rounded-[12px] bg-slate-900/90 px-4 py-3 text-white space-y-1">
                        <p className="text-sm font-bold text-[var(--brand-amber)]">
                          AI đang tạm dừng · Luồng live vẫn hoạt động
                        </p>
                        <p className="text-xs text-slate-300">
                          Đang phát cảnh an toàn cho người xem. Nhấn “Tiếp tục AI” khi sẵn sàng.
                        </p>
                      </div>
                    </div>
                  ) : null}
                </div>
              )}
            </div>

            {/* Active Product & Pending Switch Strip */}
            <div className="flex flex-col gap-3 border-t border-[var(--border-default)] p-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3 min-w-0">
                <ProductThumb skuId={snap.activeSkuId} name={snap.activeSkuName} />
                <div className="min-w-0">
                  <p className="text-xs text-[var(--text-muted)]">
                    Đang giới thiệu · {snap.activeSkuCode}
                  </p>
                  <p className="text-sm font-bold text-[var(--text-primary)] truncate">
                    {snap.activeSkuName} ·{' '}
                    <span className="tabular-nums">{formatVnd(snap.activeSkuPriceVnd)}</span>
                  </p>
                  {snap.nextSkuName ? (
                    <p className="text-xs text-[var(--text-secondary)]">
                      Kế tiếp dự kiến: {snap.nextSkuName}
                    </p>
                  ) : null}
                </div>
              </div>

              <Button
                variant="secondary"
                size="sm"
                disabled={controlsDisabled}
                leftIcon={<ArrowLeftRight className="h-3.5 w-3.5" />}
                onClick={() => {
                  setSelectedTargetSkuId(
                    snap.sessionSkus.find((s) => s.skuId !== snap.activeSkuId)?.skuId ?? '',
                  )
                  setSwitchDrawerOpen(true)
                }}
              >
                Chuyển SKU
              </Button>
            </div>

            {snap.pendingSwitch ? (
              <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--status-info-border)] bg-[var(--status-info-bg)] px-4 py-2.5 text-xs text-[var(--status-info-fg)]">
                <span>
                  Đang chờ chuyển sang <strong>{snap.pendingSwitch.targetSkuCode} · {snap.pendingSwitch.targetSkuName}</strong> (ACCEPTED — Active SKU hiện tại vẫn giữ {snap.activeSkuCode} cho tới APPLIED).
                </span>
                <Button
                  size="sm"
                  variant="primary"
                  loading={cmdMutation.isPending}
                  onClick={() =>
                    runCommand('SWITCH_SKU', {
                      targetSkuId: snap.pendingSwitch?.targetSkuId,
                      simulatePhase: 'APPLY',
                    })
                  }
                >
                  Mô phỏng APPLIED tại điểm ngắt
                </Button>
              </div>
            ) : null}
          </Card>

          {/* Expandable AI Activity & "AI sắp nói" (CR-D2=A & CR-D6=A) */}
          <Card padding="md" className="space-y-3">
            <button
              type="button"
              onClick={() => setAiExpanded((v) => !v)}
              className="flex w-full items-center justify-between text-left cursor-pointer"
            >
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-[var(--brand-amber)]" />
                <h2 className="text-sm font-bold text-[var(--text-primary)]">
                  Hoạt động AI & Nội dung sắp nói
                </h2>
                <StatusBadge label="Dự kiến · Chưa phát" tone="info" />
              </div>
              {aiExpanded ? (
                <ChevronUp className="h-4 w-4 text-[var(--text-muted)]" />
              ) : (
                <ChevronDown className="h-4 w-4 text-[var(--text-muted)]" />
              )}
            </button>

            {aiExpanded && snap.currentTurn ? (
              <div className="space-y-3 pt-2 border-t border-[var(--border-default)]">
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                  <span className="font-semibold text-[var(--text-secondary)]">
                    Giai đoạn hiện tại:{' '}
                    <strong className="text-[var(--text-primary)]">
                      {SPEECH_PHASE_LABELS[snap.currentTurn.phase] ?? snap.currentTurn.phase}
                    </strong>
                  </span>
                  <span className="text-[var(--text-muted)] tabular-nums">
                    Checkpoint kịch bản: {snap.storyCheckpointIndex}/{snap.storyTotalArcs} · Đã phát (ACK): {snap.completedTurnsCount}
                  </span>
                </div>

                <div className="rounded-[10px] bg-[var(--bg-subtle)] p-3 text-sm text-[var(--text-primary)]">
                  {snap.currentTurn.safeSummary}
                  <p className="mt-1 text-[11px] text-[var(--text-muted)]">
                    Nguồn xác minh: {snap.currentTurn.sourceRef}
                  </p>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-[11px] text-[var(--text-muted)]">
                    Story Checkpoint chỉ tiến sau khi nhận PlaybackCompleted ACK hợp lệ.
                  </p>
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={snap.currentTurn.phase === 'PLAYBACK_COMPLETED' || isStopped}
                    loading={advanceSpeechMutation.isPending}
                    onClick={() => advanceSpeechMutation.mutate()}
                  >
                    Tiến bước phát kế tiếp (Mock ACK)
                  </Button>
                </div>
              </div>
            ) : null}
          </Card>
        </div>

        {/* Right Column (40%): Comments + Pending Queue (CR-D2=A & CR-D12=A mobile tabs) */}
        <div className="lg:col-span-5 space-y-4">
          {/* Mobile tabs switch (CR-D12=A) */}
          <div className="flex rounded-[10px] border border-[var(--border-default)] bg-[var(--bg-subtle)] p-1 lg:hidden">
            <button
              type="button"
              onClick={() => setMobileTab('comments')}
              className={cn(
                'flex-1 rounded-[8px] py-2 text-xs font-semibold cursor-pointer',
                mobileTab === 'comments'
                  ? 'bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-xs'
                  : 'text-[var(--text-secondary)]',
              )}
            >
              Bình luận mới ({snap.comments.length})
            </button>
            <button
              type="button"
              onClick={() => setMobileTab('queue')}
              className={cn(
                'flex-1 rounded-[8px] py-2 text-xs font-semibold cursor-pointer',
                mobileTab === 'queue'
                  ? 'bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-xs'
                  : 'text-[var(--text-secondary)]',
              )}
            >
              Hàng đợi ưu tiên ({queuedComments.length})
            </button>
          </div>

          {/* Comments Feed */}
          <Card
            padding="md"
            className={cn('space-y-3', mobileTab === 'queue' ? 'hidden lg:block' : 'block')}
          >
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-[var(--text-primary)]">
                Bình luận mới ({snap.comments.length})
              </h2>
              <span className="text-[11px] text-[var(--text-muted)]">
                Bình luận hợp lệ không cam kết AI trả lời ngay
              </span>
            </div>

            {snap.comments.length === 0 ? (
              <p className="py-6 text-center text-xs text-[var(--text-muted)]">
                Chưa có bình luận mới. AI vẫn tiếp tục dẫn kịch bản chủ động.
              </p>
            ) : (
              <ul className="space-y-2.5 max-h-[260px] overflow-y-auto pr-1">
                {snap.comments.map((c) => (
                  <li
                    key={c.id}
                    className="rounded-[10px] border border-[var(--border-default)] bg-[var(--bg-subtle)] p-3 space-y-1"
                  >
                    <div className="flex items-center justify-between gap-2 text-xs">
                      <span className="font-bold text-[var(--text-primary)]">{c.nickname}</span>
                      <span className="text-[var(--text-muted)] tabular-nums">
                        {formatShortTime(c.receivedAt)}
                      </span>
                    </div>
                    <p className="text-xs text-[var(--text-primary)]">{c.body}</p>
                    <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
                      {c.referencedSkuCode ? (
                        <StatusBadge label={`Hỏi ${c.referencedSkuCode}`} tone="neutral" showIcon={false} />
                      ) : null}
                      <StatusBadge
                        label={
                          c.queueStatus === 'PRIORITIZED'
                            ? 'Ưu tiên'
                            : c.queueStatus === 'COMMITTED'
                              ? 'Đã chốt phát'
                              : c.queueStatus === 'PLAYED'
                                ? 'Đã phát'
                                : c.queueStatus === 'SKIPPED'
                                  ? 'Đã bỏ qua'
                                  : 'Đang chờ'
                        }
                        tone={
                          c.queueStatus === 'PRIORITIZED'
                            ? 'warning'
                            : c.queueStatus === 'PLAYED'
                              ? 'success'
                              : 'neutral'
                        }
                        showIcon={false}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          {/* Pending Queue with Prioritize / Skip pre-commit (CR-D7=A) */}
          <Card
            padding="md"
            className={cn('space-y-3', mobileTab === 'comments' ? 'hidden lg:block' : 'block')}
          >
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-[var(--text-primary)]">
                Hàng đợi câu hỏi ({queuedComments.length})
              </h2>
              <span className="text-[11px] text-[var(--text-muted)]">
                Chỉ can thiệp trước khi COMMITTED
              </span>
            </div>

            {queuedComments.length === 0 ? (
              <p className="py-4 text-center text-xs text-[var(--text-muted)]">
                Không có câu hỏi chờ xử lý trong hàng đợi.
              </p>
            ) : (
              <ul className="space-y-2.5">
                {queuedComments.map((c) => (
                  <li
                    key={c.id}
                    className="rounded-[10px] border border-[var(--border-default)] p-3 space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-xs font-bold text-[var(--text-primary)]">
                          {c.nickname} · {c.referencedSkuCode ?? 'Chung'}
                        </p>
                        <p className="text-xs text-[var(--text-secondary)]">{c.body}</p>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={controlsDisabled || c.queueStatus === 'PRIORITIZED'}
                        onClick={() => runCommand('PRIORITIZE_COMMENT', { commentId: c.id })}
                      >
                        Ưu tiên
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={controlsDisabled}
                        leftIcon={<SkipForward className="h-3.5 w-3.5" />}
                        onClick={() => runCommand('SKIP_PENDING', { commentId: c.id })}
                      >
                        Bỏ qua (Skip)
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>

      {/* Z06: Sticky Runtime Control Bar (CR-D3=A) */}
      <div className="fixed inset-x-0 bottom-0 z-30 border-t border-[var(--border-strong)] bg-[var(--bg-surface)]/95 backdrop-blur px-4 py-3 md:left-[72px] xl:left-[232px]">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            {snap.aiState === 'PAUSED' ? (
              <Button
                variant="primary"
                size="sm"
                disabled={controlsDisabled}
                loading={cmdMutation.isPending}
                leftIcon={<Play className="h-4 w-4" />}
                onClick={() => runCommand('RESUME_AI')}
              >
                Tiếp tục AI
              </Button>
            ) : (
              <Button
                variant="secondary"
                size="sm"
                disabled={controlsDisabled}
                loading={cmdMutation.isPending}
                leftIcon={<Pause className="h-4 w-4" />}
                onClick={() => runCommand('PAUSE_AI')}
              >
                Tạm dừng AI
              </Button>
            )}

            <Button
              variant="secondary"
              size="sm"
              disabled={controlsDisabled}
              leftIcon={<ArrowLeftRight className="h-4 w-4" />}
              onClick={() => {
                setSelectedTargetSkuId(
                  snap.sessionSkus.find((s) => s.skuId !== snap.activeSkuId)?.skuId ?? '',
                )
                setSwitchDrawerOpen(true)
              }}
            >
              Chuyển SKU
            </Button>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={controlsDisabled}
              leftIcon={<Square className="h-3.5 w-3.5" />}
              onClick={() => setStopModalOpen(true)}
            >
              Kết thúc phiên
            </Button>
            {isStopped ? (
              <Link to={`/studio/sessions/${sessionId}/report`}>
                <Button variant="primary" size="sm">
                  Xem báo cáo phiên
                </Button>
              </Link>
            ) : null}
          </div>
        </div>
      </div>

      {/* Switch SKU Drawer (CR-D8=A) */}
      <Drawer
        open={switchDrawerOpen}
        onClose={() => setSwitchDrawerOpen(false)}
        title="Chuyển sản phẩm đang giới thiệu (Switch SKU)"
        subtitle={`Hiện tại: ${snap.activeSkuCode} · ${snap.activeSkuName}`}
      >
        <div className="space-y-4">
          <p className="text-xs text-[var(--text-secondary)]">
            Active SKU hiện tại sẽ được giữ nguyên cho đến khi hệ thống áp dụng lệnh chuyển tại điểm ngắt an toàn (APPLIED).
          </p>
          <ul className="space-y-2.5">
            {snap.sessionSkus.map((sku) => {
              const isCurrent = sku.skuId === snap.activeSkuId
              const isSelected = sku.skuId === selectedTargetSkuId
              return (
                <li key={sku.skuId}>
                  <button
                    type="button"
                    disabled={isCurrent || !sku.eligible}
                    onClick={() => setSelectedTargetSkuId(sku.skuId)}
                    className={cn(
                      'w-full rounded-[10px] border p-3.5 text-left transition-colors cursor-pointer disabled:opacity-55 disabled:cursor-not-allowed',
                      isSelected
                        ? 'border-[var(--brand-amber)] bg-[var(--bg-hero)]'
                        : 'border-[var(--border-default)]',
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-bold">
                        {sku.skuCode} · {sku.name}
                      </span>
                      <StatusBadge
                        label={
                          isCurrent
                            ? 'Đang giới thiệu'
                            : sku.eligible
                              ? 'Đủ điều kiện'
                              : 'Bị chặn'
                        }
                        tone={isCurrent ? 'info' : sku.eligible ? 'success' : 'danger'}
                      />
                    </div>
                    <p className="mt-1 text-xs text-[var(--text-muted)]">
                      {formatVnd(sku.priceVnd)} {sku.blockerReason ? `· ${sku.blockerReason}` : ''}
                    </p>
                  </button>
                </li>
              )
            })}
          </ul>
          <div className="flex flex-col gap-2 pt-3 border-t border-[var(--border-default)]">
            <Button
              variant="primary"
              disabled={!selectedTargetSkuId}
              loading={cmdMutation.isPending}
              onClick={async () => {
                await runCommand('SWITCH_SKU', {
                  targetSkuId: selectedTargetSkuId,
                  simulatePhase: 'ACCEPT_ONLY',
                })
                setSwitchDrawerOpen(false)
              }}
            >
              Gửi yêu cầu chuyển (Chờ điểm ngắt · ACCEPTED)
            </Button>
          </div>
        </div>
      </Drawer>

      {/* Diagnostics Drawer (CR-D4=A) */}
      <Drawer
        open={diagnosticsOpen}
        onClose={() => setDiagnosticsOpen(false)}
        title="Chẩn đoán Media & Kết nối"
        subtitle={`${snap.sessionCode} · Revision v${snap.revision}`}
      >
        <div className="space-y-4 text-xs">
          <div className="rounded-[10px] bg-[var(--bg-subtle)] p-3.5 space-y-1.5">
            <p className="font-bold text-[var(--text-primary)]">Trạng thái phát sóng</p>
            <p>Session: {lifecycleCopy.label}</p>
            <p>AI Execution: {aiCopy.label}</p>
            <p>Media Health: {mediaCopy.label}</p>
            <p>Publisher: {snap.publisherState}</p>
            <p>Kết nối đồng bộ: {snap.connectionFreshness}</p>
          </div>
          {snap.fallbackModeLabel ? (
            <Banner
              severity="warning"
              title="Chế độ dự phòng đang chạy"
              description={snap.fallbackModeLabel}
            />
          ) : null}
          {isStale ? (
            <div className="flex items-center gap-2 text-[var(--status-danger-fg)]">
              <WifiOff className="h-4 w-4" />
              <span>Kết nối WebSocket mô phỏng đang gián đoạn.</span>
            </div>
          ) : null}
        </div>
      </Drawer>

      {/* Command & Activity Log Drawer (CR-D10=A) */}
      <Drawer
        open={activityLogOpen}
        onClose={() => setActivityLogOpen(false)}
        title="Nhật ký lệnh & Xử lý xung đột"
        subtitle={`${snap.sessionCode} · Ghi nhận đầy đủ actor, revision và kết quả`}
      >
        {snap.commands.length === 0 ? (
          <p className="text-xs text-[var(--text-muted)]">Chưa có lệnh vận hành nào trong phiên này.</p>
        ) : (
          <ul className="space-y-3 text-xs">
            {snap.commands.map((cmd) => (
              <li
                key={cmd.commandId}
                className="rounded-[10px] border border-[var(--border-default)] p-3 space-y-1"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-[var(--text-primary)]">
                    {cmd.type} · {cmd.actorName}
                  </span>
                  <StatusBadge
                    label={cmd.status}
                    tone={
                      cmd.status === 'APPLIED'
                        ? 'success'
                        : cmd.status === 'REJECTED'
                          ? 'danger'
                          : 'info'
                    }
                  />
                </div>
                <p className="text-[var(--text-secondary)]">{cmd.reason}</p>
                <p className="text-[11px] text-[var(--text-muted)] tabular-nums">
                  Expected rev v{cmd.expectedRevision} · Epoch {cmd.sessionEpoch} · {formatShortTime(cmd.requestedAt)}
                </p>
              </li>
            ))}
          </ul>
        )}
      </Drawer>

      {/* Stop Session Confirmation Modal */}
      <Modal
        open={stopModalOpen}
        onClose={() => setStopModalOpen(false)}
        title="Kết thúc phiên livestream?"
        description="Phiên sẽ dừng phát sóng cho toàn bộ người xem và chuyển sang trạng thái Đã kết thúc."
        footer={
          <>
            <Button variant="secondary" onClick={() => setStopModalOpen(false)}>
              Hủy
            </Button>
            <Button
              variant="primary"
              loading={cmdMutation.isPending}
              onClick={async () => {
                await runCommand('STOP', { simulatePhase: 'APPLY' })
                setStopModalOpen(false)
              }}
            >
              Xác nhận kết thúc phiên
            </Button>
          </>
        }
      >
        <p className="text-sm text-[var(--text-secondary)]">
          Sau khi kết thúc, bạn có thể mở trang Báo cáo phiên để xem thống kê và xuất dữ liệu.
        </p>
      </Modal>

      {/* Emergency Stop Quick-Confirm Modal (CR-D11=B: 1-step fast confirm, no hold, no Owner wait) */}
      <Modal
        open={emergencyModalOpen}
        onClose={() => setEmergencyModalOpen(false)}
        title="Dừng khẩn cấp livestream?"
        description="Phiên phát sẽ được kết thúc ngay để đảm bảo an toàn. Bạn không cần chờ Chủ sở hữu phê duyệt."
        footer={
          <>
            <Button variant="secondary" onClick={() => setEmergencyModalOpen(false)}>
              Hủy
            </Button>
            <Button
              variant="destructive"
              loading={cmdMutation.isPending}
              onClick={async () => {
                await runCommand('EMERGENCY_STOP')
                setEmergencyModalOpen(false)
              }}
            >
              Xác nhận dừng ngay
            </Button>
          </>
        }
      >
        <p className="text-sm text-[var(--text-secondary)]">
          Lệnh dừng khẩn cấp có mức ưu tiên cao nhất, ngắt phát ngay và tự động ghi vào nhật ký kiểm toán phiên.
        </p>
      </Modal>
    </div>
  )
}
