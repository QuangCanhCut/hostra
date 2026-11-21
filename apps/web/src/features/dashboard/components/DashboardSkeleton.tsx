import { Card } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'

export function DashboardSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Đang tải tổng quan">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-2">
          <Skeleton className="h-7 w-40" />
          <Skeleton className="h-4 w-72 max-w-full" />
        </div>
        <Skeleton className="h-10 w-36" />
      </div>

      <Card padding="lg" className="space-y-3">
        <Skeleton className="h-6 w-64 max-w-full" />
        <Skeleton className="h-4 w-96 max-w-full" />
        <Skeleton className="h-10 w-44" />
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <Card padding="md" className="lg:col-span-7 space-y-4">
          <Skeleton className="h-5 w-44" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </Card>
        <Card padding="md" className="lg:col-span-5 space-y-4">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-36 w-full" />
          <Skeleton className="h-10 w-full" />
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[1, 2, 3, 4].map((idx) => (
          <Card key={idx} padding="md" className="space-y-3">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-8 w-20" />
            <Skeleton className="h-6 w-24 rounded-full" />
          </Card>
        ))}
      </div>
    </div>
  )
}
