import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  Play,
  RefreshCw,
  Send,
  Volume2,
  VolumeX,
  WifiOff,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { ThemeToggle } from '@/components/shared/ThemeToggle'
import { BrandLogo } from '@/components/shared/BrandLogo'
import { PresenterPortrait, ProductThumb } from '@/components/shared/PortraitAvatar'
import { useScenario } from '@/hooks/useScenario'
import {
  useAdmitViewer,
  useSubmitViewerComment,
  useViewerRoom,
} from '@/features/viewer/hooks/useViewerRoom'
import { formatVnd } from '@/lib/format'

interface LocalPendingComment {
  clientSubmissionId: string
  body: string
  status: 'SENDING' | 'REJECTED'
  error?: string
}

export function ViewerLiveRoomPage() {
  const { id } = useParams<{ id: string }>()
  const sessionId = id ?? 'ses-014'
  const { isDevToolsVisible } = useScenario()
  const [searchParams] = useSearchParams()
  const inviteToken = searchParams.get('invite')
  const demoState = searchParams.get('demo') // waiting | buffering | chat-reconnect | ended | invalid

  const storageKey = `hostra-guest-${sessionId}-${inviteToken ?? 'default'}`
  const [guestSessionId, setGuestSessionId] = useState<string | null>(() => {
    try {
      return window.localStorage?.getItem(storageKey) ?? null
    } catch {
      return null
    }
  })

  const { data: room, isLoading, refetch } = useViewerRoom(
    sessionId,
    inviteToken,
    guestSessionId,
  )
  const admitMutation = useAdmitViewer(sessionId)
  const commentMutation = useSubmitViewerComment(sessionId)

  const [nickname, setNickname] = useState('')
  const [joinError, setJoinError] = useState<string | null>(null)
  const [commentText, setCommentText] = useState('')
  const [pendingLocal, setPendingLocal] = useState<LocalPendingComment | null>(null)
  const [muted, setMuted] = useState(false)
  const [simBuffering, setSimBuffering] = useState(demoState === 'buffering')
  const [simChatOffline, setSimChatOffline] = useState(demoState === 'chat-reconnect')

  const handleJoin = async () => {
    setJoinError(null)
    try {
      const updated = await admitMutation.mutateAsync({
        inviteToken,
        nickname,
        existingGuestSessionId: guestSessionId,
      })
      if (updated.guestSession) {
        setGuestSessionId(updated.guestSession.guestSessionId)
        try {
          window.localStorage?.setItem(storageKey, updated.guestSession.guestSessionId)
        } catch {
          // ignore
        }
      }
    } catch (err) {
      setJoinError(err instanceof Error ? err.message : 'Không thể tham gia phòng.')
    }
  }

  const handleSendComment = async () => {
    if (!room?.guestSession || !commentText.trim() || simChatOffline) return
    const clientSubmissionId = `sub-${Date.now()}`
    const body = commentText.trim()
    setCommentText('')
    setPendingLocal({ clientSubmissionId, body, status: 'SENDING' })
    try {
      await commentMutation.mutateAsync({
        guestSessionId: room.guestSession.guestSessionId,
        nickname: room.guestSession.nickname,
        body,
        clientSubmissionId,
      })
      setPendingLocal(null)
    } catch (err) {
      setPendingLocal({
        clientSubmissionId,
        body,
        status: 'REJECTED',
        error: err instanceof Error ? err.message : 'Không thể gửi bình luận.',
      })
    }
  }

  const effectiveAccess = demoState === 'invalid' ? 'INVALID' : room?.accessState ?? 'VALID'
  const effectiveLifecycle =
    demoState === 'waiting'
      ? 'PREPARING'
      : demoState === 'ended'
        ? 'STOPPED'
        : room?.lifecycle ?? 'LIVE'

  const header = (
    <header className="flex h-14 items-center justify-between border-b border-[var(--bg-sidebar-border)] [background:var(--bg-sidebar)] px-4 text-[#f5ebdd]">
      <BrandLogo tone="on-dark" subtitle="LIVE RIÊNG TƯ" />
      <div className="flex items-center gap-2">
        <ThemeToggle tone="on-dark" className="h-8 w-8" />
      </div>
    </header>
  )

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[var(--bg-canvas)] flex flex-col">
        {header}
        <main className="flex flex-1 items-center justify-center p-6 text-sm text-[var(--text-secondary)]">
          Đang kiểm tra liên kết mời...
        </main>
      </div>
    )
  }

  /* VWR-06: Invalid / Expired / Revoked / Exhausted Invite */
  if (effectiveAccess !== 'VALID') {
    return (
      <div className="min-h-screen bg-[var(--bg-canvas)] flex flex-col">
        {header}
        <main className="flex flex-1 items-center justify-center p-4">
          <Card featured elevated padding="lg" className="w-full max-w-sm text-center space-y-4">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[var(--status-danger-bg)] text-[var(--status-danger-fg)]">
              <AlertCircle className="h-7 w-7" />
            </div>
            <h1 className="font-display text-xl font-bold text-[var(--text-primary)]">Không thể tham gia</h1>
            <p className="text-sm text-[var(--text-secondary)]">
              {room?.accessReason ||
                'Lời mời đã hết hạn hoặc không còn hiệu lực. Vui lòng liên hệ người mời.'}
            </p>
            <Link to="/studio/invites" className="block">
              <Button variant="secondary" size="lg" className="w-full h-[50px]">
                Quay lại
              </Button>
            </Link>
          </Card>
        </main>
      </div>
    )
  }

  /* VWR-05: Session Ended (VR-D6=A: no replay/VOD) */
  if (effectiveLifecycle === 'STOPPED' || effectiveLifecycle === 'CANCELLED') {
    return (
      <div className="min-h-screen bg-[var(--bg-canvas)] flex flex-col">
        {header}
        <main className="flex flex-1 items-center justify-center p-4">
          <Card featured elevated padding="lg" className="w-full max-w-sm text-center space-y-4">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[var(--status-success-bg)] text-[var(--status-success-fg)]">
              <CheckCircle2 className="h-7 w-7" />
            </div>
            <h1 className="font-display text-xl font-bold text-[var(--text-primary)]">Phiên đã kết thúc</h1>
            <p className="text-sm text-[var(--text-secondary)]">
              Cảm ơn bạn đã theo dõi! Hẹn gặp lại ở livestream tiếp theo.
            </p>
            <Link to="/studio/dashboard" className="block">
              <Button variant="primary" size="lg" className="w-full">
                Thoát
              </Button>
            </Link>
          </Card>
        </main>
      </div>
    )
  }

  /* VWR-01: Invite Entry (Nickname Admission) */
  if (!room?.guestSession && demoState !== 'waiting' && demoState !== 'buffering' && demoState !== 'chat-reconnect') {
    return (
      <div className="min-h-screen bg-[var(--bg-canvas)] flex flex-col">
        {header}
        <main className="flex flex-1 items-center justify-center p-4">
          <Card featured elevated padding="lg" className="w-full max-w-sm space-y-5">
            <div className="flex aspect-video items-center justify-center rounded-[12px] [background:var(--bg-hero)] border border-[var(--bg-hero-border)]">
              <div className="flex h-14 w-14 items-center justify-center rounded-full [background:var(--cta-primary-bg)] text-[var(--cta-primary-fg)] shadow-[0_6px_18px_rgba(0,0,0,0.28)]">
                <Play className="h-6 w-6 fill-current ml-0.5" />
              </div>
            </div>

            <div className="text-center space-y-1">
              <h1 className="font-display text-xl font-bold text-[var(--text-primary)]">
                Tham gia livestream cùng HOSTRA
              </h1>
              <p className="text-sm text-[var(--text-secondary)]">
                {room?.sessionTitle} · {room?.merchantName}
              </p>
            </div>

            <div className="space-y-3">
              <div>
                <label htmlFor="viewer-nickname" className="block text-xs font-semibold mb-1.5">
                  Tên hiển thị của bạn
                </label>
                <input
                  id="viewer-nickname"
                  type="text"
                  value={nickname}
                  onChange={(e) => setNickname(e.target.value)}
                  placeholder="Nhập tên để tham gia..."
                  className="h-11 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm text-[var(--text-primary)] focus:border-[var(--accent-gold)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]"
                />
              </div>

              {joinError ? (
                <p className="text-xs font-medium text-[var(--status-danger-fg)]">{joinError}</p>
              ) : null}

              <Button
                variant="primary"
                size="lg"
                className="w-full"
                loading={admitMutation.isPending}
                onClick={handleJoin}
              >
                Vào phòng livestream
              </Button>
            </div>

            <p className="text-center text-xs text-[var(--text-muted)]">
              Đây là phòng xem riêng theo lời mời (chỉ xem & bình luận, không bật camera/micro).
            </p>
          </Card>
        </main>
      </div>
    )
  }

  /* VWR-02: Waiting Room (VR-D3=A: Chat locked before LIVE) */
  if (effectiveLifecycle !== 'LIVE') {
    return (
      <div className="min-h-screen bg-[var(--bg-canvas)] flex flex-col">
        {header}
        <main className="flex flex-1 items-center justify-center p-4">
          <Card featured elevated padding="lg" className="w-full max-w-sm text-center space-y-4">
            <StatusBadge
              label={effectiveLifecycle === 'STARTING' ? 'Đang chuẩn bị phát' : 'Phòng chờ'}
              tone="info"
              pulse={effectiveLifecycle === 'STARTING'}
            />
            <h1 className="font-display text-xl font-bold text-[var(--text-primary)]">
              Livestream sắp bắt đầu
            </h1>
            <p className="text-sm text-[var(--text-secondary)]">
              Bạn đã tham gia phòng chờ của <strong>{room?.sessionTitle}</strong>. Bình luận sẽ mở ngay khi phiên bắt đầu phát trực tiếp.
            </p>
            <Button
              variant="secondary"
              className="w-full"
              leftIcon={<RefreshCw className="h-4 w-4" />}
              onClick={() => refetch()}
            >
              Kiểm tra lại trạng thái
            </Button>
          </Card>
        </main>
      </div>
    )
  }

  /* VWR-03: LIVE Room (Mobile-first video top + Product Card below + Comments; Desktop 2-col) */
  return (
    <div className="min-h-screen bg-[var(--bg-canvas)] flex flex-col">
      {header}

      <main className="mx-auto w-full max-w-6xl flex-1 p-3 sm:p-5">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          {/* Video + Active Product Card (VR-D1=B, VR-D2=A, VR-D4=A) */}
          <div className="lg:col-span-7 space-y-3">
            <div className="relative aspect-video w-full overflow-hidden rounded-[14px] border border-[var(--border-strong)] bg-[var(--media-stage-bg)]">
              <PresenterPortrait
                presenterId={room?.presenterId ?? 'prs-linh-01'}
                name={room?.presenterName ?? 'AI Presenter'}
                className="h-full w-full aspect-video rounded-none border-0"
              />
              <div className="absolute top-3 left-3 flex items-center gap-2">
                <StatusBadge label="LIVE" tone="danger" pulse />
                <span className="rounded-full border border-[#5a4632]/70 bg-[#120d0a]/80 px-2.5 py-0.5 text-[11px] font-medium text-[#f5ebdd] backdrop-blur-xs">
                  Người dẫn AI
                </span>
              </div>
              <button
                type="button"
                aria-label={muted ? 'Bật âm thanh' : 'Tắt âm thanh'}
                onClick={() => setMuted((m) => !m)}
                className="absolute top-3 right-3 flex h-11 w-11 items-center justify-center rounded-full border border-[#5a4632]/60 bg-[#120d0a]/75 text-[#f5ebdd] hover:bg-[#1a130e] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)] cursor-pointer"
              >
                {muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
              </button>

              {simBuffering ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#120d0a]/85 p-4 text-center text-[#f5ebdd] backdrop-blur-[2px]">
                  <Loader2 className="h-7 w-7 animate-spin text-[#f2c47d]" />
                  <p className="mt-2 text-sm font-bold">Đang tải video...</p>
                  <p className="mt-0.5 text-xs text-[#c3b4a2]">
                    Phiên vẫn đang phát trực tiếp · Bạn vẫn có thể gửi bình luận
                  </p>
                </div>
              ) : null}
            </div>

            {/* Tiêu đề chính ngữ nghĩa cho trình đọc màn hình & chuẩn WCAG */}
            <h1 className="sr-only">
              {room?.sessionTitle ?? 'Phòng xem livestream trực tiếp HOSTRA'}
            </h1>

            {/* Thẻ sản phẩm đang giới thiệu nằm dưới khung video */}
            {room?.activeSku ? (
              <Card featured padding="sm" className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <ProductThumb skuId={room.activeSku.skuId} name={room.activeSku.name} />
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <p className="text-sm font-bold text-[var(--text-primary)] truncate">
                        {room.activeSku.name}
                      </p>
                      {room.activeSku.ocopVerified ? (
                        <StatusBadge label="OCOP đã xác minh" tone="success" />
                      ) : null}
                    </div>
                    <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                      {room.activeSku.skuCode} ·{' '}
                      <strong className="tabular-nums text-[var(--text-primary)]">
                        {formatVnd(room.activeSku.priceVnd)}
                      </strong>{' '}
                      · {room.activeSku.packSpec}
                    </p>
                  </div>
                </div>
              </Card>
            ) : null}

            {/* Nút mô phỏng chỉ hiện khi bật Dev Inspector (?devTools=1 hoặc Ctrl+Shift+D) */}
            {isDevToolsVisible ? (
              <div className="flex flex-wrap gap-2 text-[11px]">
                <button
                  type="button"
                  onClick={() => setSimBuffering((v) => !v)}
                  className="rounded-[6px] border border-[var(--border-default)] bg-[var(--bg-surface)] px-2.5 py-1.5 text-[var(--text-secondary)] cursor-pointer"
                >
                  {simBuffering ? 'Tắt mô phỏng Buffering' : 'Mô phỏng Video Buffering'}
                </button>
                <button
                  type="button"
                  onClick={() => setSimChatOffline((v) => !v)}
                  className="rounded-[6px] border border-[var(--border-default)] bg-[var(--bg-surface)] px-2.5 py-1.5 text-[var(--text-secondary)] cursor-pointer"
                >
                  {simChatOffline ? 'Kết nối lại bình luận' : 'Mô phỏng Mất kết nối bình luận'}
                </button>
              </div>
            ) : null}
          </div>

          {/* Live Comments & Composer (VR-D7=A) */}
          <Card padding="md" className="lg:col-span-5 flex flex-col justify-between gap-3 min-h-[380px]">
            <div className="space-y-3 flex-1">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-[var(--text-primary)]">
                  Bình luận trực tiếp
                </h2>
                <span className="text-[11px] text-[var(--text-muted)]">
                  {room?.guestSession?.nickname ?? 'Khách mời'}
                </span>
              </div>

              {simChatOffline ? (
                <div className="flex items-start gap-2 rounded-[10px] border border-[var(--status-warning-border)] bg-[var(--status-warning-bg)] p-3 text-xs text-[var(--status-warning-fg)]">
                  <WifiOff className="h-4 w-4 shrink-0 mt-0.5" />
                  <div>
                    <p className="font-semibold">Đang kết nối lại bình luận</p>
                    <p>Bạn vẫn có thể tiếp tục xem video.</p>
                  </div>
                </div>
              ) : null}

              <ul className="space-y-2.5 max-h-[300px] overflow-y-auto pr-1">
                {pendingLocal ? (
                  <li className="rounded-[10px] border border-[var(--accent-gold)] bg-[var(--bg-raised)] p-2.5 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold">Bạn</span>
                      <StatusBadge
                        label={pendingLocal.status === 'SENDING' ? 'Đang gửi...' : 'Không gửi được'}
                        tone={pendingLocal.status === 'SENDING' ? 'info' : 'danger'}
                      />
                    </div>
                    <p className="mt-1">{pendingLocal.body}</p>
                    {pendingLocal.error ? (
                      <p className="mt-1 text-[var(--status-danger-fg)]">{pendingLocal.error}</p>
                    ) : null}
                  </li>
                ) : null}

                {(room?.comments ?? []).map((c) => (
                  <li key={c.id} className="rounded-[10px] bg-[var(--bg-subtle)] p-2.5 text-xs">
                    <p className="font-bold text-[var(--text-primary)]">{c.nickname}</p>
                    <p className="mt-0.5 text-[var(--text-secondary)]">{c.body}</p>
                  </li>
                ))}
              </ul>
            </div>

            <div className="flex items-center gap-2 pt-2 border-t border-[var(--border-default)]">
              <input
                type="text"
                disabled={simChatOffline || !room?.guestSession}
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSendComment()
                }}
                placeholder={
                  simChatOffline ? 'Đang chờ kết nối lại...' : 'Nhập bình luận...'
                }
                className="h-10 flex-1 rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm disabled:opacity-60"
              />
              <Button
                variant="primary"
                size="md"
                aria-label="Gửi bình luận"
                disabled={simChatOffline || !commentText.trim() || !room?.guestSession}
                onClick={handleSendComment}
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </Card>
        </div>
      </main>
    </div>
  )
}
