import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, Check, Save, Send, Upload } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Banner } from '@/components/ui/Banner'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { useCreateProduct } from '@/features/products/hooks/useProducts'
import { cn } from '@/lib/cn'

const STEPS = [
  { num: 1, label: 'Thông tin sản phẩm' },
  { num: 2, label: 'Tài liệu OCOP' },
  { num: 3, label: 'Chứng từ thực phẩm' },
  { num: 4, label: 'Kiểm tra & Gửi' },
]

export function ProductWizardPage() {
  const navigate = useNavigate()
  const { data: auth } = useAuth()
  const createMutation = useCreateProduct()
  const isOwner = Boolean(auth?.capabilities.canSubmitOcop)

  const [step, setStep] = useState(1)
  const [name, setName] = useState('Hạt mắc ca sấy nứt vỏ')
  const [skuCode, setSkuCode] = useState('ML-006')
  const [category, setCategory] = useState('Thực phẩm đóng gói')
  const [priceVnd, setPriceVnd] = useState(215000)
  const [packSpec, setPackSpec] = useState('Hũ 500g kèm dụng cụ tách vỏ')
  const [origin, setOrigin] = useState('Mường Lát, Thanh Hóa')
  const [expiryLabel, setExpiryLabel] = useState('12 tháng kể từ ngày đóng gói')
  const [description, setDescription] = useState('Hạt mắc ca sấy nguyên vị, đóng hũ kín có nhãn truy xuất.')
  const [ocopDecisionCode, setOcopDecisionCode] = useState('OCOP-TH-2026-0301')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const handlePersist = async (submitForVerification: boolean) => {
    setErrorMsg(null)
    if (!name.trim() || !skuCode.trim()) {
      setErrorMsg('Vui lòng nhập đầy đủ Tên sản phẩm và Mã SKU.')
      return
    }
    try {
      const created = await createMutation.mutateAsync({
        name,
        skuCode,
        category,
        priceVnd,
        packSpec,
        origin,
        expiryLabel,
        description,
        ocopDecisionCode,
        step,
        submitForVerification,
      })
      navigate(`/studio/products/${created.skuId}?tab=ocop`)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Không thể lưu sản phẩm.')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Link
            to="/studio/products"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] mb-1"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Quay lại Danh mục sản phẩm
          </Link>
          <h1 className="font-display text-[26px] sm:text-[32px] font-bold leading-[1.16] tracking-[-0.02em] text-[var(--text-primary)]">
            {isOwner ? 'Thêm sản phẩm & Hồ sơ OCOP' : 'Tạo bản nháp sản phẩm (Vận hành viên)'}
          </h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Lưu nháp từng bước; tải tài liệu không tự tạo trạng thái OCOP đã xác minh.
          </p>
        </div>

        <Button
          variant="secondary"
          leftIcon={<Save className="h-4 w-4" />}
          loading={createMutation.isPending}
          onClick={() => handlePersist(false)}
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
                  'flex w-full items-center gap-2 rounded-[8px] border px-3 py-2.5 text-left text-xs font-semibold cursor-pointer transition-colors',
                  step === s.num
                    ? 'border-[var(--border-strong)] bg-[var(--bg-raised)] text-[var(--accent-gold)]'
                    : 'border-transparent text-[var(--text-muted)] hover:bg-[var(--bg-subtle)]',
                )}
              >
                <span
                  className={cn(
                    'flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold tabular-nums',
                    step === s.num
                      ? '[background:var(--cta-primary-bg)] text-[var(--cta-primary-fg)]'
                      : s.num < step
                        ? 'bg-[var(--status-success-bg)] text-[var(--status-success-fg)]'
                        : 'bg-[var(--bg-subtle)] text-[var(--text-muted)]',
                  )}
                >
                  {s.num < step ? <Check className="h-3.5 w-3.5" /> : s.num}
                </span>
                <span className="truncate">{s.label}</span>
              </button>
            </li>
          ))}
        </ol>
      </Card>

      {errorMsg ? <Banner severity="danger" title="Không thể lưu" description={errorMsg} /> : null}

      <Card padding="lg" className="space-y-5">
        {step === 1 ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="prod-name" className="block text-xs font-semibold mb-1.5">Tên sản phẩm *</label>
              <input id="prod-name" value={name} onChange={(e) => setName(e.target.value)} className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm" />
            </div>
            <div>
              <label htmlFor="prod-sku" className="block text-xs font-semibold mb-1.5">Mã SKU *</label>
              <input id="prod-sku" value={skuCode} onChange={(e) => setSkuCode(e.target.value)} className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm" />
            </div>
            <div>
              <label htmlFor="prod-price" className="block text-xs font-semibold mb-1.5">Giá dự kiến (VNĐ)</label>
              <input id="prod-price" type="number" value={priceVnd} onChange={(e) => setPriceVnd(Number(e.target.value))} className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm tabular-nums" />
            </div>
            <div>
              <label htmlFor="prod-spec" className="block text-xs font-semibold mb-1.5">Quy cách đóng gói</label>
              <input id="prod-spec" value={packSpec} onChange={(e) => setPackSpec(e.target.value)} className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm" />
            </div>
            <div>
              <label htmlFor="prod-origin" className="block text-xs font-semibold mb-1.5">Xuất xứ</label>
              <input id="prod-origin" value={origin} onChange={(e) => setOrigin(e.target.value)} className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm" />
            </div>
            <div>
              <label htmlFor="prod-category" className="block text-xs font-semibold mb-1.5">Nhóm hàng</label>
              <input id="prod-category" value={category} onChange={(e) => setCategory(e.target.value)} className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm" />
            </div>
          </div>
        ) : null}

        {step === 2 ? (
          <div className="space-y-4">
            <div>
              <label htmlFor="prod-ocop" className="block text-xs font-semibold mb-1.5">Số quyết định công nhận OCOP (nếu có)</label>
              <input id="prod-ocop" value={ocopDecisionCode} onChange={(e) => setOcopDecisionCode(e.target.value)} className="h-10 w-full max-w-md rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm" />
            </div>
            <div className="rounded-[12px] border-2 border-dashed border-[var(--border-strong)] bg-[var(--bg-subtle)] p-6 text-center">
              <Upload className="mx-auto h-7 w-7 text-[var(--text-secondary)]" />
              <p className="mt-2 text-sm font-semibold">Kéo thả PDF/ảnh quyết định OCOP vào đây</p>
              <p className="mt-1 text-xs text-[var(--text-muted)]">
                Lưu ý: Tải ảnh chứng nhận hoặc logo OCOP không tự động chuyển sang trạng thái Đã xác minh.
              </p>
            </div>
          </div>
        ) : null}

        {step === 3 ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="prod-exp" className="block text-xs font-semibold mb-1.5">Hạn sử dụng công bố</label>
              <input id="prod-exp" value={expiryLabel} onChange={(e) => setExpiryLabel(e.target.value)} className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm" />
            </div>
            <div className="sm:col-span-2">
              <label htmlFor="prod-desc" className="block text-xs font-semibold mb-1.5">Mô tả ngắn sản phẩm</label>
              <textarea id="prod-desc" rows={3} value={description} onChange={(e) => setDescription(e.target.value)} className="w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] p-3 text-sm" />
            </div>
          </div>
        ) : null}

        {step === 4 ? (
          <div className="space-y-4">
            <h2 className="text-base font-bold">Kiểm tra hồ sơ trước khi lưu / gửi xác minh</h2>
            <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2 rounded-[10px] bg-[var(--bg-subtle)] p-4 text-sm">
              <div><dt className="text-xs text-[var(--text-muted)]">Sản phẩm</dt><dd className="font-semibold">{name} ({skuCode})</dd></div>
              <div><dt className="text-xs text-[var(--text-muted)]">Giá dự kiến</dt><dd className="font-semibold tabular-nums">{priceVnd.toLocaleString('vi-VN')} đ</dd></div>
              <div><dt className="text-xs text-[var(--text-muted)]">Quy cách & Xuất xứ</dt><dd className="font-semibold">{packSpec} · {origin}</dd></div>
              <div><dt className="text-xs text-[var(--text-muted)]">Mã OCOP khai báo</dt><dd className="font-semibold">{ocopDecisionCode || 'Chưa nhập'}</dd></div>
            </dl>
            {!isOwner ? (
              <Banner
                severity="info"
                title="Quyền Vận hành viên (PC-D4)"
                description="Bạn có thể lưu bản nháp và gửi Chủ sở hữu rà soát. Chỉ Chủ sở hữu mới có quyền Gửi hồ sơ xác minh OCOP."
              />
            ) : null}
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
            ) : isOwner ? (
              <Button
                variant="primary"
                leftIcon={<Send className="h-4 w-4" />}
                loading={createMutation.isPending}
                onClick={() => handlePersist(true)}
              >
                Gửi hồ sơ xác minh OCOP
              </Button>
            ) : (
              <Button
                variant="primary"
                leftIcon={<Save className="h-4 w-4" />}
                loading={createMutation.isPending}
                onClick={() => handlePersist(false)}
              >
                Lưu bản nháp cho Chủ sở hữu
              </Button>
            )}
          </div>
        </div>
      </Card>
    </div>
  )
}
