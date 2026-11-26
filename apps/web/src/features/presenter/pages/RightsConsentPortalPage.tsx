import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { CheckCircle2, ShieldAlert, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Banner } from '@/components/ui/Banner'
import { BrandLogo } from '@/components/shared/BrandLogo'
import { ThemeToggle } from '@/components/shared/ThemeToggle'
import {
  useRightsConsent,
  useSubmitRightsDecision,
} from '@/features/presenter/hooks/usePresenters'
import { RIGHTS_STATUS_COPY } from '@/lib/status-copy'

export function RightsConsentPortalPage() {
  const { requestId } = useParams<{ requestId: string }>()
  const { data, isLoading } = useRightsConsent(requestId)
  const decisionMutation = useSubmitRightsDecision(requestId ?? '')
  const [notice, setNotice] = useState<string | null>(null)

  const handleDecision = async (action: 'ACCEPT' | 'DECLINE' | 'REVOKE') => {
    await decisionMutation.mutateAsync(action)
    setNotice(
      action === 'ACCEPT'
        ? 'Bạn đã xác nhận đồng thuận sử dụng hình ảnh. Trạng thái đã được đồng bộ sang Presenter Studio và Readiness.'
        : action === 'REVOKE'
          ? 'Bạn đã thu hồi quyền sử dụng. Mọi tài sản và phiên phụ thuộc đã bị khóa sử dụng.'
          : 'Bạn đã từ chối yêu cầu sử dụng hình ảnh.',
    )
  }

  const consent = data?.consent
  const statusCopy = consent ? RIGHTS_STATUS_COPY[consent.status] : null

  return (
    <div className="min-h-screen flex flex-col text-[var(--text-primary)]">
      <header className="flex h-[60px] items-center justify-between border-b border-[var(--border-default)] bg-[var(--bg-canvas)]/95 px-4 backdrop-blur-xs sm:px-8">
        <BrandLogo tone="adaptive" subtitle="CỔNG XÁC NHẬN CHỦ THỂ QUYỀN" />
        <ThemeToggle />
      </header>

      <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-10 space-y-5">
        {isLoading ? (
          <Card padding="lg" featured>Đang tải thông tin yêu cầu xác nhận quyền...</Card>
        ) : !consent ? (
          <Card padding="lg" featured>Không tìm thấy yêu cầu xác nhận quyền này.</Card>
        ) : (
          <>
            {notice ? <Banner severity="info" title="Đã ghi nhận quyết định" description={notice} /> : null}

            <Card padding="lg" featured elevated className="space-y-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h1 className="font-display text-2xl font-bold text-[var(--text-primary)]">
                    Xác nhận quyền sử dụng hình ảnh cá nhân
                  </h1>
                  <p className="mt-1.5 text-xs text-[var(--text-muted)] leading-relaxed">
                    Luồng xác nhận độc lập dành riêng cho Chủ thể quyền ({consent.subjectName}), tách biệt hoàn toàn với tài khoản Merchant Owner.
                  </p>
                </div>
                {statusCopy ? <StatusBadge label={statusCopy.label} tone={statusCopy.tone} /> : null}
              </div>

              <dl className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 rounded-[10px] border border-[var(--border-default)] bg-[var(--bg-subtle)]/70 p-4 text-xs">
                <div>
                  <dt className="text-[var(--text-muted)]">Presenter đề nghị</dt>
                  <dd className="mt-0.5 font-semibold text-[var(--text-primary)]">{data?.presenterName}</dd>
                </div>
                <div>
                  <dt className="text-[var(--text-muted)]">Phiên bản quyền</dt>
                  <dd className="mt-0.5 font-semibold text-[var(--text-primary)] tabular-nums">
                    v{consent.rightsVersion} · Hết hạn {consent.expiresAt}
                  </dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-[var(--text-muted)]">Mục đích sử dụng</dt>
                  <dd className="mt-0.5 font-medium text-[var(--text-primary)]">{consent.purpose}</dd>
                </div>
                <div>
                  <dt className="text-[var(--text-muted)]">Quyền ảnh &amp; video livestream</dt>
                  <dd className="mt-0.5 font-semibold text-[var(--text-primary)]">Có trong đề nghị</dd>
                </div>
                <div>
                  <dt className="text-[var(--text-muted)]">Quyền nhân bản giọng nói</dt>
                  <dd className="mt-0.5 font-semibold text-[var(--text-muted)]">
                    Không áp dụng (tách riêng)
                  </dd>
                </div>
              </dl>

              <div className="rounded-[10px] border border-[var(--status-info-border)] bg-[var(--status-info-bg)] px-3.5 py-2.5 text-xs text-[var(--status-info-fg)]">
                Bạn có toàn quyền từ chối hoặc thu hồi đồng thuận bất kỳ lúc nào theo chính sách bảo vệ quyền chủ thể.
              </div>

              <div className="flex flex-wrap gap-2.5 pt-2 border-t border-[var(--border-default)]">
                <Button
                  variant="primary"
                  loading={decisionMutation.isPending}
                  leftIcon={<CheckCircle2 className="h-4 w-4" />}
                  onClick={() => handleDecision('ACCEPT')}
                >
                  Tôi đồng ý cấp quyền
                </Button>
                <Button
                  variant="secondary"
                  loading={decisionMutation.isPending}
                  leftIcon={<XCircle className="h-4 w-4" />}
                  onClick={() => handleDecision('DECLINE')}
                >
                  Từ chối
                </Button>
                {consent.status === 'VERIFIED' ? (
                  <Button
                    variant="destructive"
                    loading={decisionMutation.isPending}
                    leftIcon={<ShieldAlert className="h-4 w-4" />}
                    onClick={() => handleDecision('REVOKE')}
                  >
                    Thu hồi quyền ngay
                  </Button>
                ) : null}
              </div>
            </Card>
          </>
        )}
      </main>
    </div>
  )
}
