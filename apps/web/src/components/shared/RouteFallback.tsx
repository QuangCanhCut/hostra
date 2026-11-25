import { Skeleton } from '@/components/ui/Skeleton'

export function RouteFallback() {
  return (
    <div className="space-y-4 p-6" aria-busy="true" aria-label="Đang tải trang">
      <Skeleton className="h-10 w-64 rounded-[var(--radius-md)]" />
      <div className="grid gap-4 md:grid-cols-2">
        <Skeleton className="h-44 rounded-[var(--radius-lg)]" />
        <Skeleton className="h-44 rounded-[var(--radius-lg)]" />
      </div>
    </div>
  )
}
