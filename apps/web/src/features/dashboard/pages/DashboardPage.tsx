import { Link } from 'react-router-dom'
import { AlertTriangle, Plus, RefreshCw, ShieldBan } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { useDashboard } from '@/features/dashboard/hooks/useDashboard'
import { DashboardHero } from '@/features/dashboard/components/DashboardHero'
import { ActionCenter } from '@/features/dashboard/components/ActionCenter'
import { FeaturedSessionCard } from '@/features/dashboard/components/FeaturedSessionCard'
import { AssetStatusGrid } from '@/features/dashboard/components/AssetStatusGrid'
import { RecentSessionsSection } from '@/features/dashboard/components/RecentSessionsSection'
import { DashboardSkeleton } from '@/features/dashboard/components/DashboardSkeleton'
import { ApiError } from '@/services/api-client'

export function DashboardPage() {
  const { data: auth } = useAuth()
  const { data, isLoading, isError, error, refetch, isFetching } = useDashboard()

  if (isLoading) {
    return <DashboardSkeleton />
  }

  if (isError) {
    const isForbidden = error instanceof ApiError && error.status === 403
    return (
      <EmptyState
        tone={isForbidden ? 'warning' : 'danger'}
        icon={
          isForbidden ? (
            <ShieldBan className="h-6 w-6" aria-hidden="true" />
          ) : (
            <AlertTriangle className="h-6 w-6" aria-hidden="true" />
          )
        }
        title={
          isForbidden
            ? 'Bạn không có quyền truy cập phạm vi này'
            : 'Không thể tải dữ liệu tổng quan'
        }
        description={
          error instanceof Error
            ? error.message
            : 'Đã xảy ra sự cố kết nối. Vui lòng thử tải lại.'
        }
        action={
          isForbidden ? (
            <Link to="/auth/sign-in">
              <Button variant="secondary">Quay lại trang đăng nhập</Button>
            </Link>
          ) : (
            <Button
              variant="primary"
              loading={isFetching}
              leftIcon={<RefreshCw className="h-4 w-4" />}
              onClick={() => refetch()}
            >
              Thử tải lại
            </Button>
          )
        }
      />
    )
  }

  if (!data) {
    return null
  }

  const canCreateSession = Boolean(auth?.capabilities.canCreateSession)

  return (
    <div className="space-y-6">
      {/* Z02: Page Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)] sm:text-[26px]">
            Tổng quan
          </h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Tổng quan phiên livestream và những công việc quan trọng nhất.
          </p>
        </div>

        {canCreateSession ? (
          <Link to="/studio/sessions/new" className="shrink-0">
            <Button
              variant="primary"
              size="md"
              leftIcon={<Plus className="h-4 w-4" />}
            >
              Tạo phiên mới
            </Button>
          </Link>
        ) : null}
      </div>

      {/* Z03: Critical Alerts + Next Best Action Hero */}
      <DashboardHero hero={data.hero} criticalAlerts={data.criticalAlerts} />

      {/* Z04: Two-column 60/40 (Action Center + Featured Session) */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <ActionCenter
            items={data.actionItems}
            totalCount={data.totalActionCount}
          />
        </div>
        <div className="lg:col-span-5">
          <FeaturedSessionCard
            session={data.featuredSession}
            capabilities={auth?.capabilities}
          />
        </div>
      </div>

      {/* Z05: 4 Independent Asset Status Cards */}
      <AssetStatusGrid items={data.assetCards} />

      {/* Z06: Recent Sessions (max 3) */}
      <RecentSessionsSection sessions={data.recentSessions} />
    </div>
  )
}
