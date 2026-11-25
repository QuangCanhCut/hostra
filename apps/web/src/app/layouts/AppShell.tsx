import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from '@/app/layouts/Sidebar'
import { Topbar } from '@/app/layouts/Topbar'
import { DevScenarioBar } from '@/components/shared/DevScenarioBar'
import { useAuth } from '@/features/auth/hooks/useAuth'

const ROUTE_TITLES: Array<{ match: string; label: string }> = [
  { match: '/studio/dashboard', label: 'Tổng quan' },
  { match: '/studio/onboarding', label: 'Thiết lập không gian làm việc' },
  { match: '/studio/presenters', label: 'AI Presenter' },
  { match: '/studio/products', label: 'Sản phẩm & OCOP' },
  { match: '/studio/knowledge', label: 'Tri thức & Claims' },
  { match: '/studio/sessions/new', label: 'Kế hoạch livestream' },
  { match: '/studio/sessions', label: 'Phiên livestream' },
  { match: '/studio/members', label: 'Thành viên' },
  { match: '/studio/invites', label: 'Lời mời xem live' },
  { match: '/studio/reports', label: 'Báo cáo' },
]

function resolvePageLabel(pathname: string): string {
  const found = ROUTE_TITLES.find((r) => pathname.startsWith(r.match))
  return found?.label ?? 'Merchant Studio'
}

export function AppShell() {
  const location = useLocation()
  const { data: auth } = useAuth()
  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false
    return window.matchMedia('(min-width: 768px) and (max-width: 1150px)').matches
  })
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    const media = window.matchMedia('(min-width: 768px) and (max-width: 1150px)')
    const sync = () => setCollapsed(media.matches)
    sync()
    media.addEventListener('change', sync)
    return () => media.removeEventListener('change', sync)
  }, [])

  return (
    <div
      className="flex min-h-screen text-[var(--text-primary)]"
      style={{ '--sidebar-width': collapsed ? '72px' : '248px' } as React.CSSProperties}
    >
      <Sidebar
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((prev) => !prev)}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
        actor={auth?.actor}
        workspace={auth?.workspace}
        capabilities={auth?.capabilities}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          pageLabel={resolvePageLabel(location.pathname)}
          onOpenMobileMenu={() => setMobileOpen(true)}
          actor={auth?.actor}
          workspace={auth?.workspace}
        />

        <main className="mx-auto w-full max-w-[1700px] flex-1 px-4 py-5 sm:px-6 lg:px-7 lg:py-6">
          <Outlet />
        </main>
      </div>

      <DevScenarioBar />
    </div>
  )
}
