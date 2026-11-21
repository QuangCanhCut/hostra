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
    <div className="min-h-screen bg-[var(--bg-canvas)] flex flex-col">
      <header className="flex h-16 items-center justify-between border-b border-[var(--border-default)] bg-[var(--bg-surface)] px-4 sm:px-8">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-[8px] bg-[var(--brand-amber)] text-[var(--brand-navy)] font-bold">
            H
          </div>
          <span className="text-sm font-bold tracking-wide text-[var(--text-primary)]">
            HOSTRA AI
          </span>
        </div>
        <ThemeToggle />
      </header>

      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <Card padding="lg" elevated className="w-full max-w-md space-y-6">
          <div className="rounded-[12px] bg-[var(--brand-navy)] p-5">
            <BrandLogo subtitle="MERCHANT STUDIO · ĐĂNG NHẬP" />
            <p className="mt-3 text-xs text-slate-300 leading-relaxed">
              Cổng đăng nhập tập trung (Managed OIDC) cho không gian làm việc livestream
              riêng tư của nhà bán hàng.
            </p>
          </div>

          <div className="space-y-3">
            <h1 className="text-xl font-bold text-[var(--text-primary)]">
              Đăng nhập vào Merchant Studio
            </h1>
            <p className="text-sm text-[var(--text-secondary)]">
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

          <p className="text-center text-xs text-[var(--text-muted)]">
            Khách xem livestream tham gia bằng liên kết mời và tên hiển thị, không cần tài
            khoản Merchant Studio.
          </p>
        </Card>
      </main>
    </div>
  )
}
