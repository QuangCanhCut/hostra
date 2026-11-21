import { Link } from 'react-router-dom'
import { CheckCircle2, ChevronRight, Lock } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import type { DashboardActionItem } from '@/features/dashboard/types/dashboard.types'

export interface ActionCenterProps {
  items: DashboardActionItem[]
  totalCount: number
}

export function ActionCenter({ items, totalCount }: ActionCenterProps) {
  const visibleItems = items.slice(0, 5)

  return (
    <Card id="action-center" padding="md" className="flex h-full flex-col">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-[var(--text-primary)]">
            Công việc cần xử lý
          </h2>
          <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
            Ưu tiên những tác vụ cần bạn quyết định hoặc theo dõi
          </p>
        </div>
        {totalCount > 5 ? (
          <Link
            to="/studio/sessions"
            className="text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] underline-offset-4 hover:underline shrink-0"
          >
            Xem tất cả ({totalCount})
          </Link>
        ) : null}
      </div>

      <div className="mt-4 flex-1">
        {visibleItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-[10px] border border-dashed border-[var(--border-strong)] bg-[var(--bg-subtle)] px-4 py-8 text-center">
            <CheckCircle2
              className="h-8 w-8 text-[var(--status-success-fg)]"
              aria-hidden="true"
            />
            <p className="mt-2 text-sm font-semibold text-[var(--text-primary)]">
              Không có tác vụ nào đang chờ bạn
            </p>
            <p className="mt-1 text-xs text-[var(--text-secondary)]">
              Mọi hồ sơ và công việc trong phạm vi của bạn đã được cập nhật.
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-[var(--border-default)]">
            {visibleItems.map((item) => (
              <li key={item.id}>
                <Link
                  to={item.targetRoute}
                  className="group flex flex-col gap-2 py-3.5 first:pt-1 last:pb-1 sm:flex-row sm:items-center sm:justify-between sm:gap-3 transition-colors"
                >
                  <div className="min-w-0 flex-1 space-y-1">
                    <p className="text-sm font-semibold leading-snug text-[var(--text-primary)] group-hover:underline">
                      {item.title}
                    </p>
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-[var(--text-muted)]">
                      <span>{item.resourceLabel}</span>
                      {!item.actionableByViewer && item.waitingRoleLabel ? (
                        <span className="inline-flex items-center gap-1 text-[var(--text-secondary)]">
                          <Lock className="h-3 w-3" aria-hidden="true" />
                          {item.waitingRoleLabel}
                        </span>
                      ) : null}
                    </div>
                  </div>

                  <div className="flex shrink-0 items-center justify-between gap-2 sm:justify-end">
                    <StatusBadge
                      label={item.statusLabel}
                      tone={item.statusTone}
                      className="whitespace-nowrap"
                    />
                    <ChevronRight
                      className="h-4 w-4 text-[var(--text-muted)] transition-transform duration-150 group-hover:translate-x-0.5"
                      aria-hidden="true"
                    />
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  )
}
