import { NavLink } from 'react-router-dom'
import {
  BarChart3,
  BookOpenCheck,
  CalendarClock,
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  Link2,
  PackageCheck,
  Radio,
  Sparkles,
  Users,
  X,
} from 'lucide-react'
import { BrandLogo } from '@/components/shared/BrandLogo'
import type { ActorProfile, UserCapabilities, WorkspaceSummary } from '@/types/auth'
import { cn } from '@/lib/cn'

interface NavItem {
  to: string
  label: string
  icon: typeof LayoutDashboard
  ownerOnly?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { to: '/studio/dashboard', label: 'Tổng quan', icon: LayoutDashboard },
  { to: '/studio/presenters', label: 'AI Presenter', icon: Sparkles },
  { to: '/studio/products', label: 'Sản phẩm & OCOP', icon: PackageCheck },
  { to: '/studio/knowledge', label: 'Tri thức & Claims', icon: BookOpenCheck },
  { to: '/studio/sessions/new', label: 'Kế hoạch livestream', icon: CalendarClock, ownerOnly: true },
  { to: '/studio/sessions', label: 'Phiên livestream', icon: Radio },
  { to: '/studio/members', label: 'Thành viên', icon: Users, ownerOnly: true },
  { to: '/studio/invites', label: 'Lời mời xem live', icon: Link2, ownerOnly: true },
  { to: '/studio/reports', label: 'Báo cáo', icon: BarChart3 },
]

export interface SidebarProps {
  collapsed: boolean
  onToggleCollapse: () => void
  mobileOpen: boolean
  onCloseMobile: () => void
  actor?: ActorProfile
  workspace?: WorkspaceSummary
  capabilities?: UserCapabilities
}

export function Sidebar({
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onCloseMobile,
  actor,
  workspace,
  capabilities,
}: SidebarProps) {
  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.ownerOnly || capabilities?.canManageMembers,
  )

  const sidebarContent = (isMobileDrawer: boolean) => {
    const isCompact = !isMobileDrawer && collapsed

    return (
      <div className="flex h-full flex-col bg-[var(--bg-sidebar)] text-[var(--text-sidebar)]">
        <div className="flex h-16 items-center justify-between px-4 border-b border-white/10">
          <BrandLogo collapsed={isCompact} />
          {isMobileDrawer ? (
            <button
              type="button"
              onClick={onCloseMobile}
              aria-label="Đóng thanh điều hướng"
              className="flex h-9 w-9 items-center justify-center rounded-[8px] text-slate-300 hover:bg-white/10 cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>
          ) : (
            <button
              type="button"
              onClick={onToggleCollapse}
              aria-label={isCompact ? 'Mở rộng thanh điều hướng' : 'Thu gọn thanh điều hướng'}
              className="hidden lg:flex h-8 w-8 items-center justify-center rounded-[8px] text-slate-400 hover:bg-white/10 hover:text-white cursor-pointer"
            >
              {isCompact ? (
                <ChevronRight className="h-4 w-4" />
              ) : (
                <ChevronLeft className="h-4 w-4" />
              )}
            </button>
          )}
        </div>

        <nav aria-label="Điều hướng Merchant Studio" className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {visibleItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={isMobileDrawer ? onCloseMobile : undefined}
                title={isCompact ? item.label : undefined}
                className={({ isActive }) =>
                  cn(
                    'flex min-h-[44px] items-center gap-3 rounded-[10px] px-3 py-2 text-sm font-medium transition-colors duration-150',
                    isCompact && 'justify-center px-2',
                    isActive
                      ? 'bg-[var(--bg-sidebar-active)] text-[var(--text-sidebar-active)]'
                      : 'text-slate-300 hover:bg-[var(--bg-sidebar-hover)] hover:text-white',
                  )
                }
              >
                <Icon className="h-[18px] w-[18px] shrink-0" aria-hidden="true" />
                {!isCompact ? <span className="truncate">{item.label}</span> : null}
              </NavLink>
            )
          })}
        </nav>

        <div className="border-t border-white/10 p-3">
          <div
            className={cn(
              'flex items-center gap-2.5 rounded-[10px] bg-white/5 px-2.5 py-2.5',
              isCompact && 'justify-center px-1.5',
            )}
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--brand-amber)] text-xs font-bold text-[var(--brand-navy)]">
              {actor?.initials ?? 'H'}
            </div>
            {!isCompact ? (
              <div className="min-w-0 flex-1 leading-tight">
                <p className="truncate text-xs font-semibold text-white">
                  {actor?.roleLabel ?? 'Merchant'}
                </p>
                <p className="truncate text-[11px] text-slate-400">
                  {workspace?.displayName ?? 'Workspace chính'}
                </p>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      {/* Desktop & Tablet persistent sidebar */}
      <aside
        className={cn(
          'hidden md:block shrink-0 border-r border-white/5 transition-[width] duration-200',
          collapsed ? 'w-[72px]' : 'w-[232px]',
        )}
      >
        <div className="sticky top-0 h-screen">{sidebarContent(false)}</div>
      </aside>

      {/* Mobile drawer */}
      {mobileOpen ? (
        <div className="fixed inset-0 z-40 flex md:hidden" role="dialog" aria-modal="true" aria-label="Menu điều hướng">
          <div
            className="fixed inset-0 bg-[var(--overlay-scrim)]"
            onClick={onCloseMobile}
            aria-hidden="true"
          />
          <div className="relative z-10 w-[264px] max-w-[82vw] h-full shadow-2xl">
            {sidebarContent(true)}
          </div>
        </div>
      ) : null}
    </>
  )
}
