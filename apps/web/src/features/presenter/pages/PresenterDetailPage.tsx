import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  CheckCircle2,
  Play,
  RefreshCw,
  ShieldAlert,
  Sparkles,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Banner } from '@/components/ui/Banner'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { PresenterPortrait } from '@/components/shared/PortraitAvatar'
import { useAuth } from '@/features/auth/hooks/useAuth'
import {
  useApprovePresenter,
  useGeneratePresenter,
  usePresenterDetail,
  useRetryPresenterClip,
} from '@/features/presenter/hooks/usePresenters'
import { RIGHTS_STATUS_COPY } from '@/lib/status-copy'
import { formatShortTime } from '@/lib/format'

export function PresenterDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: auth } = useAuth()
  const { data: presenter, isLoading } = usePresenterDetail(id)
  const generateMutation = useGeneratePresenter(id ?? '')
  const retryClipMutation = useRetryPresenterClip(id ?? '')
  const approveMutation = useApprovePresenter(id ?? '')

  const [selectedPackId, setSelectedPackId] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const isOwner = Boolean(auth?.capabilities.canManagePresenters)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (!presenter) {
    return (
      <EmptyState
        icon={<Sparkles className="h-6 w-6" />}
        title="Không tìm thấy AI Presenter"
        description="Tài nguyên này không tồn tại hoặc nằm ngoài phạm vi workspace."
        action={
          <Link to="/studio/presenters">
            <Button variant="secondary">Quay lại thư viện</Button>
          </Link>
        }
      />
    )
  }

  const rightsCopy = RIGHTS_STATUS_COPY[presenter.rightsStatus]
  const activePackId =
    selectedPackId ?? presenter.selectedCandidateId ?? presenter.candidates[0]?.packId ?? null
  const activePack = presenter.candidates.find((c) => c.packId === activePackId) ?? null
  const canCompareAB = presenter.candidates.length >= 2
  const canGenerate = isOwner && presenter.rightsStatus === 'VERIFIED'
  const canApprove =
    isOwner &&
    presenter.rightsStatus === 'VERIFIED' &&
    Boolean(activePack) &&
    activePack?.qcStatus === 'PASS'

  const handleGenerate = async () => {
    setErrorMsg(null)
    setFeedback(null)
    try {
      await generateMutation.mutateAsync()
      setFeedback('Đã tạo candidate mới (mô phỏng). Phiên bản đã duyệt cũ vẫn được giữ nguyên cho đến khi bạn phê duyệt bản mới.')
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Không thể tạo clip.')
    }
  }

  const handleRetryClip = async () => {
    setErrorMsg(null)
    setFeedback(null)
    try {
      await retryClipMutation.mutateAsync()
      setFeedback('Đã tạo lại riêng clip lỗi và gom thành phiên bản gói mới đạt QC.')
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Không thể tạo lại clip.')
    }
  }

  const handleApprove = async (decision: 'APPROVE' | 'REWORK') => {
    if (!activePack) return
    setErrorMsg(null)
    setFeedback(null)
    try {
      await approveMutation.mutateAsync({ packId: activePack.packId, decision })
      setFeedback(
        decision === 'APPROVE'
          ? `Đã phê duyệt ${activePack.versionLabel} làm phiên bản chính thức.`
          : 'Đã ghi nhận yêu cầu chỉnh sửa lại gói clip.',
      )
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Không thể phê duyệt.')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Link
            to="/studio/presenters"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] mb-1"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Quay lại Thư viện Presenter
          </Link>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">
              {presenter.displayName}
            </h1>
            <StatusBadge label={rightsCopy.label} tone={rightsCopy.tone} />
          </div>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Phong cách {presenter.styleLabel} · {presenter.voicePresetLabel}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Link to={`/rights/consent/${presenter.rightsConsent.requestId}`}>
            <Button variant="secondary" size="sm" leftIcon={<ShieldAlert className="h-4 w-4" />}>
              Mở Cổng xác nhận quyền
            </Button>
          </Link>
          {isOwner ? (
            <Button
              variant="primary"
              size="sm"
              disabled={!canGenerate}
              loading={generateMutation.isPending}
              leftIcon={<Sparkles className="h-4 w-4" />}
              onClick={handleGenerate}
            >
              Tạo gói clip mới
            </Button>
          ) : null}
        </div>
      </div>

      {presenter.rightsStatus !== 'VERIFIED' ? (
        <Banner
          severity={presenter.rightsStatus === 'REVOKED' ? 'danger' : 'warning'}
          title={
            presenter.rightsStatus === 'REVOKED'
              ? 'Quyền hình ảnh đã bị thu hồi — Khóa sử dụng'
              : 'Đang chờ Chủ thể quyền xác nhận'
          }
          description="Hệ thống khóa nút Tạo clip và Phê duyệt khi quyền hình ảnh chưa ở trạng thái hợp lệ. Mở Cổng xác nhận quyền để mô phỏng thao tác của Rights Subject."
          action={
            <Link to={`/rights/consent/${presenter.rightsConsent.requestId}`}>
              <Button variant="secondary" size="sm">
                Đi tới Cổng quyền
              </Button>
            </Link>
          }
        />
      ) : null}

      {feedback ? <Banner severity="info" title="Cập nhật thành công" description={feedback} /> : null}
      {errorMsg ? <Banner severity="danger" title="Không thể thực hiện" description={errorMsg} /> : null}

      {/* Preview / Comparison Area */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <Card padding="md" className="lg:col-span-7 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-base font-bold text-[var(--text-primary)]">
                {canCompareAB
                  ? 'So sánh phiên bản Video A / B'
                  : 'Xem trước: Ảnh chân dung gốc ↔ Gói clip đầu tiên'}
              </h2>
              <p className="text-xs text-[var(--text-secondary)]">
                {canCompareAB
                  ? 'Có từ 2 gói candidate trở lên — bạn có thể so sánh cùng mẫu chuyển động và chọn bản cần duyệt.'
                  : 'Mới có tối đa 1 gói clip; chế độ so sánh 2 video A/B chỉ mở khi có ít nhất 2 phiên bản candidate.'}
              </p>
            </div>
            <StatusBadge
              label={canCompareAB ? 'A/B sẵn sàng' : 'Bản tạo đầu tiên'}
              tone={canCompareAB ? 'info' : 'neutral'}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-semibold text-[var(--text-secondary)]">
                  {canCompareAB ? presenter.candidates[0].versionLabel : 'Ảnh chân dung gốc'}
                </p>
                {canCompareAB ? <StatusBadge label="Bản A · v1" tone="neutral" /> : null}
              </div>
              <div className="relative">
                <PresenterPortrait presenterId={presenter.id} name={presenter.displayName} />
                {canCompareAB ? (
                  <div className="absolute bottom-2 left-2 right-2 flex items-center justify-between rounded-[8px] bg-slate-900/80 px-3 py-1.5 text-xs text-white">
                    <span>Bản xem trước minh họa tĩnh · v1</span>
                    <span className="tabular-nums">3 clips</span>
                  </div>
                ) : null}
              </div>
              <p className="text-xs text-[var(--text-muted)]">
                {canCompareAB
                  ? `${presenter.candidates[0].motionTemplate} · Nhịp điệu tiêu chuẩn · QC: Đạt`
                  : presenter.portraitNote}
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-semibold text-[var(--text-secondary)]">
                  {canCompareAB
                    ? presenter.candidates[presenter.candidates.length - 1].versionLabel
                    : activePack
                      ? activePack.versionLabel
                      : 'Chưa có video tạo xong'}
                </p>
                {canCompareAB ? <StatusBadge label="Bản B · v2" tone="info" /> : null}
              </div>
              {activePack ? (
                <div className="relative">
                  <PresenterPortrait presenterId={presenter.id} name={presenter.displayName} />
                  <div className="absolute bottom-2 left-2 right-2 flex items-center justify-between rounded-[8px] bg-[var(--brand-navy)]/90 px-3 py-1.5 text-xs text-white">
                    <span className="inline-flex items-center gap-1.5">
                      <Play className="h-3.5 w-3.5 text-[var(--brand-amber)]" />
                      Bản xem trước minh họa · {activePack.clips.length} clips
                    </span>
                    <span className="tabular-nums">v{presenter.candidates.indexOf(activePack) + 1}</span>
                  </div>
                </div>
              ) : (
                <div className="flex aspect-[4/3] items-center justify-center rounded-[10px] border border-dashed border-[var(--border-strong)] bg-[var(--bg-subtle)] p-4 text-center text-xs text-[var(--text-muted)]">
                  Chưa có gói clip nào. Hoàn tất xác nhận quyền để bắt đầu tạo clip.
                </div>
              )}
              <p className="text-[11px] text-[var(--text-muted)]">
                Lưu ý: Đây là bản xem trước minh họa tĩnh trong môi trường mock, chưa phải video chuyển động thật để đánh giá lip-sync.
              </p>
            </div>
          </div>

          {presenter.candidates.length > 0 ? (
            <div className="space-y-2 pt-3 border-t border-[var(--border-default)]">
              <p className="text-xs font-semibold text-[var(--text-secondary)]">
                Chọn phiên bản gói để kiểm tra QC & duyệt:
              </p>
              <div className="flex flex-wrap gap-2">
                {presenter.candidates.map((cand) => {
                  const isSelected = cand.packId === activePack?.packId
                  const isApproved = cand.packId === presenter.approvedPackId
                  return (
                    <button
                      key={cand.packId}
                      type="button"
                      onClick={() => setSelectedPackId(cand.packId)}
                      className={
                        isSelected
                          ? 'rounded-[8px] border border-[var(--brand-amber)] bg-[var(--bg-hero)] px-3 py-2 text-xs font-semibold text-[var(--text-primary)] cursor-pointer'
                          : 'rounded-[8px] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2 text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] cursor-pointer'
                      }
                    >
                      {cand.versionLabel} {isApproved ? '· Đang áp dụng' : ''}
                    </button>
                  )
                })}
              </div>
            </div>
          ) : null}
        </Card>

        {/* QC & Approval Panel */}
        <Card padding="md" className="lg:col-span-5 flex flex-col justify-between gap-4">
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-bold text-[var(--text-primary)]">
                Kiểm tra chất lượng (QC) & Phê duyệt
              </h2>
              <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                {presenter.jobStageLabel}
              </p>
            </div>

            {activePack ? (
              <ul className="space-y-2.5">
                {activePack.clips.map((clip) => (
                  <li
                    key={clip.id}
                    className="rounded-[10px] border border-[var(--border-default)] bg-[var(--bg-subtle)] p-3 space-y-1.5"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold text-[var(--text-primary)]">
                        {clip.label}
                      </span>
                      <StatusBadge
                        label={clip.qcStatus === 'PASS' ? 'Đạt QC' : 'Lỗi QC'}
                        tone={clip.qcStatus === 'PASS' ? 'success' : 'danger'}
                      />
                    </div>
                    <p className="text-[11px] text-[var(--text-muted)] tabular-nums">
                      Thời lượng: {clip.durationSec} giây
                    </p>
                    {clip.qcNote ? (
                      <p className="text-xs text-[var(--status-danger-fg)]">{clip.qcNote}</p>
                    ) : null}
                    {clip.qcStatus === 'FAIL' && isOwner ? (
                      <Button
                        variant="secondary"
                        size="sm"
                        className="mt-1"
                        loading={retryClipMutation.isPending}
                        leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
                        onClick={handleRetryClip}
                      >
                        Tạo lại riêng clip lỗi này
                      </Button>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-[var(--text-muted)]">
                Chưa có kết quả QC.
              </p>
            )}

            <div className="rounded-[10px] border border-[var(--border-default)] p-3 text-xs space-y-1">
              <p className="font-semibold text-[var(--text-primary)]">Thông tin quyền & liên kết</p>
              <p className="text-[var(--text-secondary)]">
                Chủ thể: {presenter.rightsConsent.subjectName} · Hạn dùng: {presenter.rightsConsent.expiresAt}
              </p>
              <p className="text-[var(--text-muted)]">
                Phiên đang tham chiếu:{' '}
                {presenter.linkedSessionCodes.length > 0
                  ? presenter.linkedSessionCodes.join(', ')
                  : 'Chưa gắn vào phiên nào'}
              </p>
              <p className="text-[var(--text-muted)] tabular-nums">
                Cập nhật: {formatShortTime(presenter.updatedAt)}
              </p>
            </div>
          </div>

          {isOwner ? (
            <div className="flex flex-wrap gap-2 pt-3 border-t border-[var(--border-default)]">
              <Button
                variant="primary"
                className="flex-1"
                disabled={!canApprove}
                loading={approveMutation.isPending}
                leftIcon={<CheckCircle2 className="h-4 w-4" />}
                onClick={() => handleApprove('APPROVE')}
              >
                Phê duyệt phiên bản này
              </Button>
              <Button
                variant="secondary"
                disabled={!activePack}
                loading={approveMutation.isPending}
                onClick={() => handleApprove('REWORK')}
              >
                Yêu cầu sửa
              </Button>
            </div>
          ) : (
            <p className="text-xs text-[var(--text-muted)] pt-2 border-t border-[var(--border-default)]">
              Vận hành viên chỉ có quyền xem. Chỉ Chủ sở hữu mới được phê duyệt phiên bản Presenter.
            </p>
          )}
        </Card>
      </div>
    </div>
  )
}
