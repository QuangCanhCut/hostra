import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  Check,
  GripVertical,
  Lock,
  Plus,
  Save,
  Trash2,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Banner } from '@/components/ui/Banner'
import { EmptyState } from '@/components/ui/EmptyState'
import { ProductThumb } from '@/components/shared/PortraitAvatar'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { usePresenters } from '@/features/presenter/hooks/usePresenters'
import { useProducts } from '@/features/products/hooks/useProducts'
import {
  useCreateSession,
  useSessionDetail,
  useUpdateSession,
} from '@/features/live-session/hooks/useSessions'
import { OCOP_STATUS_COPY } from '@/lib/status-copy'
import { cn } from '@/lib/cn'

const STEPS = [
  { num: 1, label: 'Chọn Presenter & SKU' },
  { num: 2, label: 'Mục tiêu & Ràng buộc' },
  { num: 3, label: 'Kế hoạch nội dung' },
  { num: 4, label: 'Kiểm tra & Lưu' },
]

export function SessionWizardPage() {
  const { id } = useParams<{ id: string }>()
  const isEditing = Boolean(id)
  const navigate = useNavigate()
  const { data: auth } = useAuth()
  const { data: presentersRes, isLoading: isLoadingPresenters } = usePresenters()
  const { data: productsRes, isLoading: isLoadingProducts } = useProducts()
  const { data: existingSession, isLoading: isLoadingSession } = useSessionDetail(id)
  const createMutation = useCreateSession()
  const updateMutation = useUpdateSession(id ?? '')

  const [step, setStep] = useState(1)
  const [title, setTitle] = useState('Giới thiệu Đặc sản OCOP Mường Lát cuối tuần')
  const [presenterId, setPresenterId] = useState('prs-linh-01')
  const [selectedSkuIds, setSelectedSkuIds] = useState<string[]>([
    'sku-ml-001',
    'sku-ml-002',
    'sku-ml-004',
  ])
  const [goal, setGoal] = useState('Giới thiệu chi tiết nguồn gốc, giá niêm yết và cách bảo quản đặc sản OCOP')
  const [theme, setTheme] = useState('Đặc sản vùng cao đạt chuẩn OCOP')
  const [estimatedMinutes, setEstimatedMinutes] = useState(30)
  const [prioritySkuId, setPrioritySkuId] = useState<string>('sku-ml-001')
  const [mandatoryMessages, setMandatoryMessages] = useState(
    'Luôn nêu rõ giá niêm yết theo hồ sơ đã duyệt và không đưa tuyên bố chữa bệnh.',
  )
  const [draggedSku, setDraggedSku] = useState<string | null>(null)
  const [warningMsg, setWarningMsg] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  useEffect(() => {
    if (!existingSession) return
    setTitle(existingSession.title)
    setPresenterId(existingSession.presenterId)
    setSelectedSkuIds(existingSession.selectedSkuIds)
    setGoal(existingSession.goal)
    setTheme(existingSession.theme)
    setEstimatedMinutes(existingSession.estimatedMinutes)
    if (existingSession.prioritySkuId) setPrioritySkuId(existingSession.prioritySkuId)
    setMandatoryMessages(existingSession.mandatoryMessages)
  }, [existingSession])

  if (auth && !auth.capabilities.canCreateSession) {
    return (
      <EmptyState
        tone="warning"
        icon={<Lock className="h-6 w-6" />}
        title="Chỉ Chủ sở hữu mới được thiết lập phiên trước khi phát"
        description="Quyền chỉnh sửa Session Setup trước live của Vận hành viên đang mở (OPEN), mặc định chỉ cấp cho Chủ sở hữu."
        action={
          <Link to="/studio/sessions">
            <Button variant="secondary">Quay lại Danh sách phiên</Button>
          </Link>
        }
      />
    )
  }

  const presenters = presentersRes?.items ?? []
  const products = productsRes?.items ?? []
  const isCatalogLoading = isLoadingPresenters || isLoadingProducts || (isEditing && isLoadingSession)

  if (isCatalogLoading) {
    return (
      <div className="space-y-6" aria-busy="true" aria-label="Đang tải dữ liệu phiên">
        <div className="h-8 w-64 animate-pulse rounded-[8px] bg-[var(--bg-subtle)]" />
        <Card padding="lg" className="space-y-4">
          <div className="h-10 w-full animate-pulse rounded-[8px] bg-[var(--bg-subtle)]" />
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <div className="h-64 animate-pulse rounded-[12px] bg-[var(--bg-subtle)]" />
            <div className="h-64 animate-pulse rounded-[12px] bg-[var(--bg-subtle)]" />
          </div>
        </Card>
      </div>
    )
  }

  const addSku = (skuId: string) => {
    setWarningMsg(null)
    if (selectedSkuIds.includes(skuId)) {
      setWarningMsg('Sản phẩm này đã có trong danh sách phiên (không được chọn trùng).')
      return
    }
    if (selectedSkuIds.length >= 5) {
      setWarningMsg('Mỗi phiên livestream chỉ được chọn tối đa 5 SKU. Hãy gỡ bớt 1 sản phẩm trước khi thêm.')
      return
    }
    setSelectedSkuIds((prev) => [...prev, skuId])
  }

  const removeSku = (skuId: string) => {
    setWarningMsg(null)
    setSelectedSkuIds((prev) => prev.filter((x) => x !== skuId))
  }

  const moveSku = (index: number, delta: -1 | 1) => {
    const target = index + delta
    if (target < 0 || target >= selectedSkuIds.length) return
    const next = [...selectedSkuIds]
    const [item] = next.splice(index, 1)
    next.splice(target, 0, item)
    setSelectedSkuIds(next)
  }

  const handleSave = async (goTo: 'story' | 'readiness') => {
    setErrorMsg(null)
    try {
      if (isEditing && id) {
        await updateMutation.mutateAsync({
          title,
          presenterId,
          selectedSkuIds,
          goal,
          theme,
          estimatedMinutes,
          prioritySkuId,
          mandatoryMessages,
        })
        navigate(`/studio/sessions/${id}/${goTo}`)
      } else {
        const created = await createMutation.mutateAsync({
          title,
          presenterId,
          selectedSkuIds,
          goal,
          theme,
          estimatedMinutes,
          prioritySkuId,
          mandatoryMessages,
        })
        navigate(`/studio/sessions/${created.id}/${goTo}`)
      }
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Không thể lưu phiên livestream.')
    }
  }

  const selectedProducts = selectedSkuIds
    .map((sid) => products.find((p) => p.skuId === sid))
    .filter((p): p is NonNullable<typeof p> => Boolean(p))

  const hasIneligibleSku = selectedProducts.some((p) => p.ocopStatus !== 'VERIFIED')

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
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            {isEditing ? `Chỉnh sửa ${existingSession?.code ?? 'phiên'}` : 'Tạo phiên livestream mới'}
          </h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Chọn Presenter, kéo-thả 2–5 sản phẩm và lưu nháp bất cứ lúc nào. Khởi chạy chỉ thực hiện ở trang Readiness riêng.
          </p>
        </div>

        <Button
          variant="secondary"
          leftIcon={<Save className="h-4 w-4" />}
          loading={createMutation.isPending || updateMutation.isPending}
          onClick={() => handleSave('story')}
        >
          Lưu bản nháp
        </Button>
      </div>

      <Card padding="sm">
        <ol className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {STEPS.map((s) => (
            <li key={s.num}>
              <button
                type="button"
                onClick={() => setStep(s.num)}
                className={cn(
                  'flex w-full items-center gap-2 rounded-[10px] px-3 py-2.5 text-left text-xs font-semibold cursor-pointer',
                  step === s.num
                    ? 'bg-[var(--bg-hero)] border border-[var(--bg-hero-border)] text-[var(--text-primary)]'
                    : 'text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)]',
                )}
              >
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--bg-subtle)] text-xs font-bold">
                  {s.num < step ? <Check className="h-3.5 w-3.5" /> : s.num}
                </span>
                <span className="truncate">{s.label}</span>
              </button>
            </li>
          ))}
        </ol>
      </Card>

      {warningMsg ? <Banner severity="warning" title="Lưu ý chọn SKU" description={warningMsg} /> : null}
      {errorMsg ? <Banner severity="danger" title="Không thể lưu" description={errorMsg} /> : null}

      <Card padding="lg" className="space-y-6">
        {step === 1 ? (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <label htmlFor="ses-title" className="block text-xs font-semibold mb-1.5">
                  Tên phiên livestream *
                </label>
                <input
                  id="ses-title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm"
                />
              </div>
              <div>
                <label htmlFor="ses-presenter" className="block text-xs font-semibold mb-1.5">
                  AI Presenter sử dụng
                </label>
                <select
                  id="ses-presenter"
                  value={presenterId}
                  onChange={(e) => setPresenterId(e.target.value)}
                  className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm"
                >
                  {presenters.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.displayName} ({p.activePackVersion} · {p.rightsStatus === 'VERIFIED' ? 'Quyền hợp lệ' : 'Cần xử lý quyền'})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* 2-Column SKU Picker (SS-X2: Drag & Drop + Keyboard/Touch alternative) */}
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-bold">Kho sản phẩm ({products.length} SKU)</h2>
                  <span className="text-xs text-[var(--text-muted)]">Kéo sang phải hoặc bấm + Thêm</span>
                </div>
                <ul className="space-y-2.5">
                  {products.map((prod) => {
                    const already = selectedSkuIds.includes(prod.skuId)
                    const ocop = OCOP_STATUS_COPY[prod.ocopStatus]
                    return (
                      <li
                        key={prod.skuId}
                        draggable={!already}
                        onDragStart={() => setDraggedSku(prod.skuId)}
                        className="flex items-center justify-between gap-3 rounded-[10px] border border-[var(--border-default)] bg-[var(--bg-surface)] p-3"
                      >
                        <div className="flex min-w-0 items-center gap-2.5">
                          <GripVertical className="h-4 w-4 text-[var(--text-muted)] shrink-0 hidden sm:block" />
                          <ProductThumb skuId={prod.skuId} name={prod.name} className="h-10 w-10" />
                          <div className="min-w-0">
                            <p className="text-sm font-semibold text-[var(--text-primary)] truncate">
                              {prod.name}
                            </p>
                            <div className="mt-0.5 flex flex-wrap items-center gap-1.5">
                              <span className="text-xs text-[var(--text-muted)]">{prod.skuCode}</span>
                              <StatusBadge label={ocop.label} tone={ocop.tone} />
                            </div>
                          </div>
                        </div>
                        <Button
                          size="sm"
                          variant={already ? 'ghost' : 'secondary'}
                          disabled={already}
                          leftIcon={<Plus className="h-3.5 w-3.5" />}
                          onClick={() => addSku(prod.skuId)}
                        >
                          {already ? 'Đã chọn' : 'Thêm'}
                        </Button>
                      </li>
                    )
                  })}
                </ul>
              </div>

              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => {
                  if (draggedSku) {
                    addSku(draggedSku)
                    setDraggedSku(null)
                  }
                }}
                className="space-y-3 rounded-[12px] border-2 border-dashed border-[var(--border-strong)] bg-[var(--bg-subtle)] p-4"
              >
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-bold">
                    Sản phẩm trong phiên ({selectedProducts.length}/5 SKU)
                  </h2>
                  <StatusBadge
                    label={
                      selectedProducts.length >= 2 && selectedProducts.length <= 5
                        ? 'Đạt số lượng 2–5'
                        : 'Cần từ 2 đến 5 SKU'
                    }
                    tone={selectedProducts.length >= 2 && selectedProducts.length <= 5 ? 'success' : 'warning'}
                  />
                </div>

                {hasIneligibleSku ? (
                  <p className="rounded-[8px] bg-[var(--status-warning-bg)] px-3 py-2 text-xs text-[var(--status-warning-fg)]">
                    Lưu ý: Có SKU chưa đạt OCOP đã xác minh. Bạn vẫn có thể lưu bản nháp nhưng phiên sẽ bị chặn Start tại Readiness.
                  </p>
                ) : null}

                {selectedProducts.length === 0 ? (
                  <p className="py-8 text-center text-xs text-[var(--text-muted)]">
                    Kéo thả sản phẩm vào đây hoặc bấm nút “Thêm” ở cột bên trái.
                  </p>
                ) : (
                  <ol className="space-y-2">
                    {selectedProducts.map((prod, idx) => (
                      <li
                        key={prod.skuId}
                        className="flex items-center justify-between gap-2 rounded-[10px] border border-[var(--border-default)] bg-[var(--bg-surface)] p-3"
                      >
                        <div className="flex min-w-0 items-center gap-2.5">
                          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--brand-navy)] text-xs font-bold text-white tabular-nums">
                            {idx + 1}
                          </span>
                          <div className="min-w-0">
                            <p className="text-sm font-semibold truncate">{prod.name}</p>
                            <p className="text-xs text-[var(--text-muted)]">{prod.skuCode}</p>
                          </div>
                        </div>
                        <div className="flex shrink-0 items-center gap-1">
                          <button
                            type="button"
                            aria-label={`Đưa ${prod.name} lên`}
                            disabled={idx === 0}
                            onClick={() => moveSku(idx, -1)}
                            className="flex h-8 w-8 items-center justify-center rounded-[6px] border border-[var(--border-default)] hover:bg-[var(--bg-subtle)] disabled:opacity-40 cursor-pointer"
                          >
                            <ArrowUp className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            aria-label={`Đưa ${prod.name} xuống`}
                            disabled={idx === selectedProducts.length - 1}
                            onClick={() => moveSku(idx, 1)}
                            className="flex h-8 w-8 items-center justify-center rounded-[6px] border border-[var(--border-default)] hover:bg-[var(--bg-subtle)] disabled:opacity-40 cursor-pointer"
                          >
                            <ArrowDown className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            aria-label={`Gỡ ${prod.name}`}
                            onClick={() => removeSku(prod.skuId)}
                            className="flex h-8 w-8 items-center justify-center rounded-[6px] border border-[var(--border-default)] text-[var(--status-danger-fg)] hover:bg-[var(--status-danger-bg)] cursor-pointer"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            </div>
          </div>
        ) : null}

        {step === 2 ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label htmlFor="ses-goal" className="block text-xs font-semibold mb-1.5">Mục tiêu phiên livestream</label>
              <input id="ses-goal" value={goal} onChange={(e) => setGoal(e.target.value)} className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm" />
            </div>
            <div>
              <label htmlFor="ses-theme" className="block text-xs font-semibold mb-1.5">Chủ đề chính</label>
              <input id="ses-theme" value={theme} onChange={(e) => setTheme(e.target.value)} className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm" />
            </div>
            <div>
              <label htmlFor="ses-duration" className="block text-xs font-semibold mb-1.5">Thời lượng dự kiến (phút)</label>
              <input id="ses-duration" type="number" min={10} max={180} value={estimatedMinutes} onChange={(e) => setEstimatedMinutes(Number(e.target.value))} className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm tabular-nums" />
            </div>
            <div>
              <label htmlFor="ses-priority" className="block text-xs font-semibold mb-1.5">SKU ưu tiên giới thiệu</label>
              <select id="ses-priority" value={prioritySkuId} onChange={(e) => setPrioritySkuId(e.target.value)} className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm">
                {selectedProducts.map((p) => (
                  <option key={p.skuId} value={p.skuId}>
                    {p.skuCode} · {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="sm:col-span-2">
              <label htmlFor="ses-msg" className="block text-xs font-semibold mb-1.5">Thông điệp bắt buộc (phải có nguồn tri thức đã duyệt)</label>
              <textarea id="ses-msg" rows={3} value={mandatoryMessages} onChange={(e) => setMandatoryMessages(e.target.value)} className="w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] p-3 text-sm" />
            </div>
          </div>
        ) : null}

        {step === 3 ? (
          <div className="space-y-4">
            <h2 className="text-base font-bold">Chuyển sang Story Planner sau khi lưu cấu hình</h2>
            <p className="text-sm text-[var(--text-secondary)]">
              Kế hoạch nội dung sẽ tự động tạo các Story Arcs tương ứng với {selectedProducts.length} SKU bạn đã chọn theo đúng thứ tự. Bất kỳ thay đổi SKU nào sau này sẽ yêu cầu duyệt lại Story Plan.
            </p>
            <ol className="space-y-2 rounded-[10px] bg-[var(--bg-subtle)] p-4 text-sm">
              {selectedProducts.map((p, i) => (
                <li key={p.skuId} className="font-medium">
                  {i + 1}. {p.name} ({p.skuCode})
                </li>
              ))}
            </ol>
          </div>
        ) : null}

        {step === 4 ? (
          <div className="space-y-4">
            <h2 className="text-base font-bold">Xác nhận cấu hình phiên livestream</h2>
            <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2 rounded-[10px] bg-[var(--bg-subtle)] p-4 text-sm">
              <div><dt className="text-xs text-[var(--text-muted)]">Tên phiên</dt><dd className="font-semibold">{title}</dd></div>
              <div><dt className="text-xs text-[var(--text-muted)]">Số sản phẩm</dt><dd className="font-semibold tabular-nums">{selectedSkuIds.length} SKU</dd></div>
              <div><dt className="text-xs text-[var(--text-muted)]">Thời lượng ước tính</dt><dd className="font-semibold tabular-nums">{estimatedMinutes} phút</dd></div>
              <div><dt className="text-xs text-[var(--text-muted)]">Trạng thái sau lưu</dt><dd className="font-semibold">Đang chuẩn bị (Chưa Start)</dd></div>
            </dl>
          </div>
        ) : null}

        <div className="flex flex-wrap items-center justify-between gap-2 pt-4 border-t border-[var(--border-default)]">
          <Button variant="secondary" disabled={step === 1} onClick={() => setStep((s) => Math.max(1, s - 1))}>
            Quay lại
          </Button>
          <div className="flex flex-wrap gap-2">
            {step < 4 ? (
              <Button variant="primary" onClick={() => setStep((s) => Math.min(4, s + 1))}>
                Tiếp tục
              </Button>
            ) : (
              <>
                <Button
                  variant="secondary"
                  loading={createMutation.isPending || updateMutation.isPending}
                  onClick={() => handleSave('readiness')}
                >
                  Lưu & Mở Readiness
                </Button>
                <Button
                  variant="primary"
                  loading={createMutation.isPending || updateMutation.isPending}
                  onClick={() => handleSave('story')}
                >
                  Lưu & Mở Story Planner
                </Button>
              </>
            )}
          </div>
        </div>
      </Card>
    </div>
  )
}
