import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, BookOpenCheck, PackageCheck, Radio, Save, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Banner } from '@/components/ui/Banner'
import { PageHeader } from '@/components/ui/PageHeader'
import { FormField, TextInput } from '@/components/ui/FormField'
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
      <PageHeader
        title="Thiết lập không gian làm việc"
        subtitle="Lưu nháp linh hoạt — các tác vụ chạy nền (tạo AI Presenter, xác minh OCOP) không khóa bước chuẩn bị."
        actions={
          isOwner ? (
            <Button
              variant="primary"
              leftIcon={<Save className="h-4 w-4" />}
              loading={saveMutation.isPending}
              onClick={handleSaveDraft}
            >
              Lưu bản nháp
            </Button>
          ) : null
        }
      />

      {savedNotice ? <Banner severity="info" title="Đã lưu nháp" description={savedNotice} /> : null}

      <Card padding="lg" featured className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <FormField label="Tên hiển thị Workspace" htmlFor="ob-ws">
          <TextInput
            id="ob-ws"
            value={workspaceName}
            onChange={(e) => setWorkspaceName(e.target.value)}
            disabled={!isOwner}
          />
        </FormField>
        <FormField label="Đơn vị / HTX chủ quản" htmlFor="ob-legal">
          <TextInput
            id="ob-legal"
            value={merchantLegalName}
            onChange={(e) => setMerchantLegalName(e.target.value)}
            disabled={!isOwner}
          />
        </FormField>
        <FormField label="Nhóm sản phẩm trọng tâm" htmlFor="ob-cat" className="sm:col-span-2">
          <TextInput
            id="ob-cat"
            value={categoryFocus}
            onChange={(e) => setCategoryFocus(e.target.value)}
            disabled={!isOwner}
          />
        </FormField>
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
              <Card padding="md" className="h-full space-y-2.5 transition-colors group-hover:border-[var(--accent-gold)]">
                <Icon className="h-5 w-5 text-[var(--accent-gold)]" aria-hidden="true" />
                <p className="text-sm font-bold text-[var(--text-primary)] group-hover:text-[var(--accent-gold)] transition-colors">
                  {step.label}
                </p>
                <p className="text-xs text-[var(--text-muted)] leading-relaxed">{step.desc}</p>
                <span className="inline-flex items-center gap-1 pt-1 text-xs font-semibold text-[var(--accent-gold)]">
                  Thực hiện <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                </span>
              </Card>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
