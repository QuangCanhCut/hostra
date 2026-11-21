import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, BookOpenCheck, PackageCheck, Radio, Save, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Banner } from '@/components/ui/Banner'
import {
  useOnboardingDraft,
  useSaveOnboardingDraft,
} from '@/features/live-session/hooks/useSessions'
import { useAuth } from '@/features/auth/hooks/useAuth'

export function OnboardingPage() {
  const { data: auth } = useAuth()
  const { data: draft } = useOnboardingDraft()
  const saveMutation = useSaveOnboardingDraft()

  const [workspaceName, setWorkspaceName] = useState('Đặc sản Mường Lát')
  const [merchantLegalName, setMerchantLegalName] = useState('HTX Nông sản & Đặc sản Mường Lát')
  const [categoryFocus, setCategoryFocus] = useState('Thực phẩm đóng gói & OCOP vùng cao')
  const [savedNotice, setSavedNotice] = useState<string | null>(null)

  useEffect(() => {
    if (!draft) return
    setWorkspaceName(draft.workspaceName)
    setMerchantLegalName(draft.merchantLegalName)
    setCategoryFocus(draft.categoryFocus)
  }, [draft])

  const isOwner = Boolean(auth?.capabilities.canCreateSession)

  const handleSaveDraft = async () => {
    await saveMutation.mutateAsync({
      workspaceName,
      merchantLegalName,
      categoryFocus,
      step: 2,
    })
    setSavedNotice('Đã lưu bản nháp thiết lập Workspace. Bạn có thể rời trang và quay lại tiếp tục bất cứ lúc nào.')
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            Thiết lập Workspace & Bắt đầu nhanh
          </h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Lưu nháp linh hoạt theo AW-D2 — các tác vụ chạy nền (tạo Presenter, xác minh OCOP) không khóa bước chuẩn bị.
          </p>
        </div>
        {isOwner ? (
          <Button
            variant="primary"
            leftIcon={<Save className="h-4 w-4" />}
            loading={saveMutation.isPending}
            onClick={handleSaveDraft}
          >
            Lưu bản nháp
          </Button>
        ) : null}
      </div>

      {savedNotice ? <Banner severity="info" title="Đã lưu nháp" description={savedNotice} /> : null}

      <Card padding="lg" className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="ob-ws" className="block text-xs font-semibold mb-1.5">Tên hiển thị Workspace</label>
          <input id="ob-ws" value={workspaceName} onChange={(e) => setWorkspaceName(e.target.value)} disabled={!isOwner} className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm disabled:opacity-60" />
        </div>
        <div>
          <label htmlFor="ob-legal" className="block text-xs font-semibold mb-1.5">Đơn vị / HTX chủ quản</label>
          <input id="ob-legal" value={merchantLegalName} onChange={(e) => setMerchantLegalName(e.target.value)} disabled={!isOwner} className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm disabled:opacity-60" />
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="ob-cat" className="block text-xs font-semibold mb-1.5">Nhóm sản phẩm trọng tâm</label>
          <input id="ob-cat" value={categoryFocus} onChange={(e) => setCategoryFocus(e.target.value)} disabled={!isOwner} className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm disabled:opacity-60" />
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { to: '/studio/presenters/new', label: '1. Tạo AI Presenter', desc: 'Tải ảnh, gửi yêu cầu quyền và chọn phong cách', icon: Sparkles },
          { to: '/studio/products/new', label: '2. Thêm 2–5 sản phẩm', desc: 'Nhập thông tin thực phẩm và hồ sơ OCOP', icon: PackageCheck },
          { to: '/studio/knowledge', label: '3. Duyệt Tri thức & Claims', desc: 'Đối chiếu tài liệu nguồn và loại claim rủi ro', icon: BookOpenCheck },
          { to: '/studio/sessions/new', label: '4. Lập phiên đầu tiên', desc: 'Chọn SKU, lập Story Plan và kiểm tra Readiness', icon: Radio },
        ].map((step) => {
          const Icon = step.icon
          return (
            <Link key={step.to} to={step.to} className="group block">
              <Card padding="md" className="h-full space-y-2 group-hover:border-[var(--border-strong)] transition-colors">
                <Icon className="h-5 w-5 text-[var(--text-secondary)]" />
                <p className="text-sm font-bold text-[var(--text-primary)]">{step.label}</p>
                <p className="text-xs text-[var(--text-secondary)]">{step.desc}</p>
                <span className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--text-primary)] pt-1">
                  Thực hiện <ArrowRight className="h-3.5 w-3.5" />
                </span>
              </Card>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
