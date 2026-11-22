import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ChevronDown, HelpCircle, LogOut, Menu, Settings } from 'lucide-react'
import { ThemeToggle } from '@/components/shared/ThemeToggle'
import type { ActorProfile, WorkspaceSummary } from '@/types/auth'

export interface TopbarProps {
  pageLabel: string
  onOpenMobileMenu: () => void
  actor?: ActorProfile
  workspace?: WorkspaceSummary
}

export function Topbar({
  pageLabel,
  onOpenMobileMenu,
  actor,
  workspace,
}: TopbarProps) {
  const navigate = useNavigate()
  const [accountMenuOpen, setAccountMenuOpen] = useState(false)
  const menuContainerRef = useRef<HTMLDivElement>(null)
  const triggerButtonRef = useRef<HTMLButtonElement>(null)

  /* Đóng Account Menu khi nhấn Escape (khôi phục focus về nút Avatar) hoặc bấm ra ngoài */
  useEffect(() => {
    if (!accountMenuOpen) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        setAccountMenuOpen(false)
        triggerButtonRef.current?.focus()
      }
    }

    const handlePointerDown = (event: MouseEvent) => {
      if (
        menuContainerRef.current &&
        !menuContainerRef.current.contains(event.target as Node)
      ) {
        setAccountMenuOpen(false)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('mousedown', handlePointerDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('mousedown', handlePointerDown)
    }
  }, [accountMenuOpen])

  const handleOpenWorkspaceSetup = () => {
    setAccountMenuOpen(false)
    navigate('/studio/onboarding')
  }

  /* Đăng xuất mô phỏng: điều hướng về màn hình đăng nhập, không xóa dữ liệu phiên/sản phẩm trong mock store */
  const handleMockSignOut = () => {
    setAccountMenuOpen(false)
    navigate('/auth/sign-in')
  }

  const displayName = actor?.displayName ?? 'Tài khoản'
  const roleLabel = actor?.roleLabel ?? 'Thành viên'
  const emailOrRole = actor?.email ?? roleLabel
  const workspaceName = workspace?.displayName ?? 'Merchant Studio'

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b border-[var(--border-default)] bg-[var(--bg-surface)] px-4 sm:px-6 lg:px-8">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          onClick={onOpenMobileMenu}
          aria-label="Mở menu điều hướng"
          className="inline-flex h-10 w-10 items-center justify-center rounded-[8px] border border-[var(--border-default)] text-[var(--text-primary)] hover:bg-[var(--bg-subtle)] md:hidden cursor-pointer"
        >
          <Menu className="h-5 w-5" />
        </button>

        <nav aria-label="Đường dẫn trang" className="flex min-w-0 items-center gap-1.5 text-sm">
          <span className="hidden sm:inline text-[var(--text-muted)] truncate">
            {workspaceName}
          </span>
          <span className="hidden sm:inline text-[var(--text-muted)]">/</span>
          <span className="font-semibold text-[var(--text-primary)] truncate">
            {pageLabel}
          </span>
        </nav>
      </div>

      <div className="flex items-center gap-2 sm:gap-2.5">
        <ThemeToggle />
        <Link
          to="/auth/sign-in"
          aria-label="Chuyển tài khoản mô phỏng"
          title="Chuyển tài khoản mô phỏng"
          className="inline-flex h-10 w-10 items-center justify-center rounded-[8px] border border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]"
        >
          <HelpCircle className="h-4 w-4" aria-hidden="true" />
        </Link>

        {/* PO-D01: Account Dropdown Menu trên Avatar góc trên bên phải */}
        <div ref={menuContainerRef} className="relative">
          <button
            ref={triggerButtonRef}
            type="button"
            aria-haspopup="menu"
            aria-expanded={accountMenuOpen}
            aria-label={`Menu tài khoản ${displayName}`}
            onClick={() => setAccountMenuOpen((prev) => !prev)}
            className="inline-flex min-h-10 items-center gap-2 rounded-full border border-[var(--border-default)] bg-[var(--bg-subtle)] py-1 pl-1.5 pr-2 sm:pr-3 text-left transition-colors hover:border-[var(--border-strong)] hover:bg-[var(--bg-surface)] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]"
          >
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--brand-navy)] text-[11px] font-bold text-white">
              {actor?.initials ?? 'H'}
            </span>
            <span className="hidden sm:inline max-w-[140px] truncate text-xs font-medium text-[var(--text-primary)]">
              {displayName}
            </span>
            <ChevronDown
              className={`h-3.5 w-3.5 shrink-0 text-[var(--text-muted)] transition-transform duration-150 ${
                accountMenuOpen ? 'rotate-180' : ''
              }`}
              aria-hidden="true"
            />
          </button>

          {accountMenuOpen ? (
            <div
              role="menu"
              aria-label="Tùy chọn tài khoản"
              className="absolute right-0 mt-2 w-64 origin-top-right rounded-[12px] border border-[var(--border-default)] bg-[var(--bg-surface)] p-1.5 shadow-lg z-40"
            >
              {/* Thông tin tài khoản hiện tại */}
              <div className="border-b border-[var(--border-default)] px-3 py-2.5">
                <p className="truncate text-sm font-semibold text-[var(--text-primary)]">
                  {displayName}
                </p>
                <p className="mt-0.5 truncate text-xs text-[var(--text-secondary)]">
                  {emailOrRole}
                </p>
                <p className="mt-1 truncate text-[11px] font-medium text-[var(--text-muted)]">
                  {roleLabel} · {workspaceName}
                </p>
              </div>

              <div className="py-1">
                <button
                  type="button"
                  role="menuitem"
                  onClick={handleOpenWorkspaceSetup}
                  className="flex min-h-10 w-full items-center gap-2.5 rounded-[8px] px-3 py-2 text-left text-sm font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-subtle)] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]"
                >
                  <Settings className="h-4 w-4 shrink-0 text-[var(--text-secondary)]" aria-hidden="true" />
                  <span>Thiết lập không gian làm việc</span>
                </button>
              </div>

              <div className="border-t border-[var(--border-default)] pt-1">
                <button
                  type="button"
                  role="menuitem"
                  onClick={handleMockSignOut}
                  className="flex min-h-10 w-full items-center gap-2.5 rounded-[8px] px-3 py-2 text-left text-sm font-medium text-[var(--status-danger-fg)] transition-colors hover:bg-[var(--status-danger-bg)] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]"
                >
                  <LogOut className="h-4 w-4 shrink-0" aria-hidden="true" />
                  <span>Đăng xuất</span>
                </button>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  )
}
