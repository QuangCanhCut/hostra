import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Check,
  Lock,
  Save,
  ShieldCheck,
  Upload,
  Volume2,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Banner } from '@/components/ui/Banner'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { EmptyState } from '@/components/ui/EmptyState'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { useCreatePresenter } from '@/features/presenter/hooks/usePresenters'
import type { PresenterStylePreset } from '@/types/domain'
import { cn } from '@/lib/cn'

const STYLE_PRESETS: Array<{
  id: PresenterStylePreset
  name: string
  tagline: string
  description: string
}> = [
  {
    id: 'CHUYEN_NGHIEP',
    name: 'Chuyên nghiệp',
    tagline: 'Trang trọng · Rõ ràng',
    description: 'Cử chỉ tiết chế, phù hợp giải thích nguồn gốc OCOP, thành phần và quy chuẩn chất lượng.',
  },
  {
    id: 'THAN_THIEN',
    name: 'Thân thiện',
    tagline: 'Gần gũi · Tự nhiên',
    description: 'Cử chỉ mở, nhịp điệu nhẹ nhàng, tạo cảm giác trò chuyện gần gũi với khách mời.',
  },
  {
    id: 'NANG_DONG',
    name: 'Năng động',
    tagline: 'Tươi sáng · Linh hoạt',
    description: 'Chuyển động nhấn nhá rõ ràng khi giới thiệu đặc điểm nổi bật của từng sản phẩm.',
  },
]

const VOICE_PRESETS = [
  'Giọng nữ miền Bắc · Chuẩn cấp phép',
  'Giọng nữ miền Nam · Chuẩn cấp phép',
  'Giọng trung tính · Chuẩn cấp phép',
]

const STEPS = [
  { num: 1, label: 'Ảnh chân dung' },
  { num: 2, label: 'Quyền sử dụng' },
  { num: 3, label: 'Phong cách & Giọng' },
  { num: 4, label: 'Xem trước & Lưu' },
]

export function PresenterWizardPage() {
  const navigate = useNavigate()
  const { data: auth } = useAuth()
  const createMutation = useCreatePresenter()

  const [step, setStep] = useState(1)
  const [displayName, setDisplayName] = useState('Hương — Đặc sản Thanh Hóa')
  const [subjectName, setSubjectName] = useState('Lê Thị Thu Hương')
  const [portraitFileName, setPortraitFileName] = useState('chan_dung_studio_huong.jpg')
  const [stylePreset, setStylePreset] = useState<PresenterStylePreset>('THAN_THIEN')
  const [voicePresetLabel, setVoicePresetLabel] = useState(VOICE_PRESETS[0])
  const [draftNotice, setDraftNotice] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  if (auth && !auth.capabilities.canManagePresenters) {
    return (
      <EmptyState
        tone="warning"
        icon={<Lock className="h-6 w-6" />}
        title="Chỉ Chủ sở hữu mới có quyền tạo AI Presenter"
        description="Tài khoản Vận hành viên chỉ được xem thông tin Presenter trong phạm vi được cấp."
        action={
          <Link to="/studio/presenters">
            <Button variant="secondary">Quay lại thư viện Presenter</Button>
          </Link>
        }
      />
    )
  }

  const handleSave = async () => {
    setErrorMsg(null)
    if (!displayName.trim() || !subjectName.trim()) {
      setErrorMsg('Vui lòng nhập đầy đủ tên Presenter và họ tên Chủ thể quyền.')
      return
    }
    try {
      const created = await createMutation.mutateAsync({
        displayName,
        subjectName,
        portraitFileName,
        stylePreset,
        voicePresetLabel,
        step,
      })
      setDraftNotice('Đã lưu bản nháp và tạo liên kết gửi Chủ thể quyền xác nhận.')
      navigate(`/studio/presenters/${created.id}`)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Không thể lưu Presenter.')
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
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            Tạo AI Presenter mới
          </h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Tải ảnh chân dung hợp lệ, gửi yêu cầu quyền độc lập và chọn 1 trong 3 phong cách.
          </p>
        </div>

        <Button
          variant="secondary"
          leftIcon={<Save className="h-4 w-4" />}
          loading={createMutation.isPending}
          onClick={handleSave}
        >
          Lưu bản nháp
        </Button>
      </div>

      {/* Stepper */}
      <Card padding="sm">
        <ol className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {STEPS.map((s) => {
            const active = s.num === step
            const done = s.num < step
            return (
              <li key={s.num}>
                <button
                  type="button"
                  onClick={() => setStep(s.num)}
                  className={cn(
                    'flex w-full items-center gap-2.5 rounded-[10px] px-3 py-2.5 text-left text-xs font-semibold transition-colors cursor-pointer',
                    active
                      ? 'bg-[var(--bg-hero)] border border-[var(--bg-hero-border)] text-[var(--text-primary)]'
                      : 'hover:bg-[var(--bg-subtle)] text-[var(--text-secondary)]',
                  )}
                >
                  <span
                    className={cn(
                      'flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold tabular-nums',
                      active
                        ? 'bg-[var(--brand-amber)] text-[var(--text-on-amber)]'
                        : done
                          ? 'bg-[var(--status-success-bg)] text-[var(--status-success-fg)]'
                          : 'bg-[var(--bg-subtle)] text-[var(--text-muted)]',
                    )}
                  >
                    {done ? <Check className="h-3.5 w-3.5" /> : s.num}
                  </span>
                  <span className="truncate">{s.label}</span>
                </button>
              </li>
            )
          })}
        </ol>
      </Card>

      {errorMsg ? (
        <Banner severity="danger" title="Không thể tiếp tục" description={errorMsg} />
      ) : null}
      {draftNotice ? (
        <Banner severity="info" title="Đã lưu bản nháp" description={draftNotice} />
      ) : null}

      <Card padding="lg" className="space-y-6">
        {step === 1 ? (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="space-y-4">
              <div>
                <label htmlFor="prs-name" className="block text-xs font-semibold text-[var(--text-primary)] mb-1.5">
                  Tên hiển thị Presenter *
                </label>
                <input
                  id="prs-name"
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm text-[var(--text-primary)]"
                />
              </div>
              <div>
                <label htmlFor="prs-subject" className="block text-xs font-semibold text-[var(--text-primary)] mb-1.5">
                  Họ tên Chủ thể quyền trong ảnh (Rights Subject) *
                </label>
                <input
                  id="prs-subject"
                  type="text"
                  value={subjectName}
                  onChange={(e) => setSubjectName(e.target.value)}
                  className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm text-[var(--text-primary)]"
                />
              </div>
            </div>

            <div className="flex flex-col items-center justify-center rounded-[12px] border-2 border-dashed border-[var(--border-strong)] bg-[var(--bg-subtle)] p-6 text-center">
              <Upload className="h-8 w-8 text-[var(--text-secondary)]" aria-hidden="true" />
              <p className="mt-2 text-sm font-semibold text-[var(--text-primary)]">
                Ảnh chân dung một người, rõ mặt và đủ sáng
              </p>
              <p className="mt-1 text-xs text-[var(--text-secondary)]">
                Tệp mẫu đang chọn: <span className="font-medium text-[var(--text-primary)]">{portraitFileName}</span>
              </p>
              <Button
                variant="secondary"
                size="sm"
                className="mt-3"
                onClick={() => setPortraitFileName('chan_dung_studio_moi.jpg')}
              >
                Chọn ảnh chân dung mẫu khác
              </Button>
            </div>
          </div>
        ) : null}

        {step === 2 ? (
          <div className="space-y-4">
            <Banner
              severity="warning"
              title="Quyền sử dụng hình ảnh phải do Chủ thể quyền tự xác nhận"
              description="Chủ sở hữu không thể tự đánh dấu Đã xác minh thay cho người trong ảnh. Sau khi lưu bản nháp, hệ thống sẽ tạo liên kết Cổng xác nhận quyền riêng cho chủ thể."
            />
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="rounded-[10px] border border-[var(--border-default)] p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-[var(--text-primary)]">
                    Phạm vi hình ảnh & video livestream
                  </span>
                  <StatusBadge label="Bắt buộc xác nhận" tone="warning" />
                </div>
                <p className="text-xs text-[var(--text-secondary)]">
                  Áp dụng cho tạo clip chuyển động và phát trong phòng livestream riêng tư của HOSTRA. Chủ thể có thể thu hồi quyền bất cứ lúc nào.
                </p>
              </div>
              <div className="rounded-[10px] border border-[var(--border-default)] bg-[var(--bg-subtle)] p-4 space-y-2 opacity-80">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-[var(--text-primary)]">
                    Nhân bản giọng nói (Voice Cloning)
                  </span>
                  <StatusBadge label="Chưa mở trong MVP" tone="neutral" />
                </div>
                <p className="text-xs text-[var(--text-secondary)]">
                  Quyền dùng ảnh không bao gồm quyền nhân bản giọng nói. MVP mặc định dùng giọng đọc đã cấp phép (Licensed Voice Preset).
                </p>
              </div>
            </div>
          </div>
        ) : null}

        {step === 3 ? (
          <div className="space-y-6">
            <div>
              <h2 className="text-base font-bold text-[var(--text-primary)]">
                Chọn 1 trong 3 phong cách trình diễn
              </h2>
              <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                Chọn một phong cách phù hợp với sản phẩm. Không sử dụng ô nhập prompt tự do để tránh sai lệch khuôn mặt.
              </p>

              <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
                {STYLE_PRESETS.map((preset) => {
                  const selected = stylePreset === preset.id
                  return (
                    <button
                      key={preset.id}
                      type="button"
                      onClick={() => setStylePreset(preset.id)}
                      aria-pressed={selected}
                      className={cn(
                        'flex flex-col justify-between rounded-[12px] border p-4 text-left transition-colors cursor-pointer',
                        selected
                          ? 'border-[var(--brand-amber)] bg-[var(--bg-hero)] ring-2 ring-[var(--brand-amber)]/40'
                          : 'border-[var(--border-default)] bg-[var(--bg-surface)] hover:border-[var(--border-strong)]',
                      )}
                    >
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-bold text-[var(--text-primary)]">
                            {preset.name}
                          </span>
                          {selected ? (
                            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[var(--brand-amber)] text-[var(--text-on-amber)]">
                              <Check className="h-3.5 w-3.5" />
                            </span>
                          ) : null}
                        </div>
                        <p className="text-xs font-medium text-[var(--text-muted)]">
                          {preset.tagline}
                        </p>
                        <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                          {preset.description}
                        </p>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="space-y-3 pt-4 border-t border-[var(--border-default)]">
              <div className="flex items-center gap-2">
                <Volume2 className="h-4 w-4 text-[var(--text-secondary)]" aria-hidden="true" />
                <h3 className="text-sm font-bold text-[var(--text-primary)]">
                  Giọng đọc được cấp phép (Mặc định)
                </h3>
              </div>
              <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
                {VOICE_PRESETS.map((v) => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => setVoicePresetLabel(v)}
                    className={cn(
                      'rounded-[10px] border px-3.5 py-3 text-left text-xs font-medium cursor-pointer',
                      voicePresetLabel === v
                        ? 'border-[var(--brand-amber)] bg-[var(--bg-hero)] text-[var(--text-primary)] font-semibold'
                        : 'border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-secondary)]',
                    )}
                  >
                    {v}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : null}

        {step === 4 ? (
          <div className="space-y-4">
            <h2 className="text-base font-bold text-[var(--text-primary)]">
              Xác nhận bản nháp trước khi gửi yêu cầu quyền
            </h2>
            <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2 rounded-[10px] bg-[var(--bg-subtle)] p-4 text-sm">
              <div>
                <dt className="text-xs text-[var(--text-muted)]">Tên Presenter</dt>
                <dd className="font-semibold text-[var(--text-primary)]">{displayName}</dd>
              </div>
              <div>
                <dt className="text-xs text-[var(--text-muted)]">Chủ thể quyền</dt>
                <dd className="font-semibold text-[var(--text-primary)]">{subjectName}</dd>
              </div>
              <div>
                <dt className="text-xs text-[var(--text-muted)]">Phong cách</dt>
                <dd className="font-semibold text-[var(--text-primary)]">
                  {STYLE_PRESETS.find((s) => s.id === stylePreset)?.name}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-[var(--text-muted)]">Giọng đọc</dt>
                <dd className="font-semibold text-[var(--text-primary)]">{voicePresetLabel}</dd>
              </div>
            </dl>
            <div className="flex items-start gap-2.5 rounded-[10px] border border-[var(--status-info-border)] bg-[var(--status-info-bg)] p-3.5 text-xs text-[var(--status-info-fg)]">
              <ShieldCheck className="h-4 w-4 shrink-0 mt-0.5" aria-hidden="true" />
              <span>
                Sau khi lưu, hệ thống sẽ giữ Presenter ở trạng thái chờ quyền và khóa nút Tạo clip cho tới khi Chủ thể quyền xác nhận tại Cổng quyền độc lập.
              </span>
            </div>
          </div>
        ) : null}

        <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-[var(--border-default)]">
          <Button
            variant="secondary"
            disabled={step === 1}
            onClick={() => setStep((s) => Math.max(1, s - 1))}
          >
            Quay lại
          </Button>
          <div className="flex items-center gap-2">
            {step < 4 ? (
              <Button variant="primary" onClick={() => setStep((s) => Math.min(4, s + 1))}>
                Tiếp tục
              </Button>
            ) : (
              <Button
                variant="primary"
                loading={createMutation.isPending}
                onClick={handleSave}
              >
                Tạo bản nháp & Gửi yêu cầu quyền
              </Button>
            )}
          </div>
        </div>
      </Card>
    </div>
  )
}
