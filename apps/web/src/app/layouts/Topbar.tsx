import { Link } from 'react-router-dom'
import { HelpCircle, Menu } from 'lucide-react'
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
            {workspace?.displayName ?? 'Merchant Studio'}
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
          className="inline-flex h-10 w-10 items-center justify-center rounded-[8px] border border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)]"
        >
          <HelpCircle className="h-4 w-4" aria-hidden="true" />
        </Link>
        <div className="hidden sm:flex items-center gap-2 rounded-full border border-[var(--border-default)] bg-[var(--bg-subtle)] py-1 pl-1.5 pr-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--brand-navy)] text-[11px] font-bold text-white">
            {actor?.initials ?? 'H'}
          </div>
          <span className="text-xs font-medium text-[var(--text-primary)]">
            {actor?.displayName ?? 'Tài khoản'}
          </span>
        </div>
      </div>
    </header>
  )
}
