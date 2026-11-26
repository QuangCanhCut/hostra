import { useNavigate } from 'react-router-dom'
import { ShieldCheck, UserCog } from 'lucide-react'
import { BrandLogo } from '@/components/shared/BrandLogo'
import { ThemeToggle } from '@/components/shared/ThemeToggle'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { useScenario } from '@/hooks/useScenario'

export function SignInPage() {
  const navigate = useNavigate()
  const { setRole } = useScenario()

  const handleEnterAs = (role: 'OWNER' | 'OPERATOR') => {
    setRole(role)
    navigate('/studio/dashboard')
  }

  return (
    <div className="min-h-screen flex flex-col text-[var(--text-primary)]">
      <header className="flex h-[60px] items-center justify-between border-b border-[var(--border-default)] bg-[var(--bg-canvas)]/95 px-4 backdrop-blur-xs sm:px-8">
        <BrandLogo tone="adaptive" subtitle="AI LIVESTREAM" />
        <ThemeToggle />
      </header>

      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <Card padding="lg" featured elevated className="w-full max-w-[460px] space-y-6">
          <div className="rounded-[12px] border border-[var(--border-strong)] [background:var(--bg-hero)] p-5 text-[#f5ebdd]">
            <BrandLogo tone="on-dark" subtitle="MERCHANT STUDIO · ĐĂNG NHẬP" />
            <p className="mt-3 text-xs leading-relaxed text-[#e6d8c5]">
              Cổng đăng nhập tập trung (Managed OIDC) cho không gian làm việc livestream
              riêng tư của nhà bán hàng.
            </p>
          </div>

          <div className="space-y-2">
            <h1 className="font-display text-2xl font-bold text-[var(--text-primary)]">
              Đăng nhập vào Merchant Studio
            </h1>
            <p className="text-sm text-[var(--text-muted)]">
              Chọn vai trò mô phỏng để trải nghiệm luồng quản trị và phân quyền trong bản
              dựng giao diện.
            </p>
          </div>

          <div className="space-y-2.5">
            <Button
              size="lg"
              className="w-full"
              leftIcon={<ShieldCheck className="h-4 w-4" />}
              onClick={() => handleEnterAs('OWNER')}
            >
              Tiếp tục với vai trò Chủ sở hữu (Owner)
            </Button>
            <Button
              variant="secondary"
              size="lg"
              className="w-full"
              leftIcon={<UserCog className="h-4 w-4" />}
              onClick={() => handleEnterAs('OPERATOR')}
            >
              Tiếp tục với vai trò Vận hành viên (Operator)
            </Button>
          </div>

          <div className="rounded-[10px] border border-[var(--status-info-border)] bg-[var(--status-info-bg)] px-3.5 py-2.5 text-xs text-[var(--status-info-fg)]">
            Khách xem livestream tham gia bằng liên kết mời và tên hiển thị, không cần tài
            khoản Merchant Studio.
          </div>
        </Card>
      </main>
    </div>
  )
}
