import { Link } from 'react-router-dom'
import {
  BookOpenCheck,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  Lock,
  PackageCheck,
  PlayCircle,
  ShieldAlert,
} from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import type { DashboardActionItem } from '@/features/dashboard/types/dashboard.types'

export interface ActionCenterProps {
  items: DashboardActionItem[]
  totalCount: number
}

function ActionItemIcon({ item }: { item: DashboardActionItem }) {
  if (item.priority === 'CRITICAL') {
    return <ShieldAlert className="h-[18px] w-[18px] shrink-0 text-[var(--status-danger-fg)]" aria-hidden="true" />
  }
  if (item.targetRoute.includes('/presenters')) {
    return <PlayCircle className="h-[18px] w-[18px] shrink-0 text-[var(--accent-gold)]" aria-hidden="true" />
  }
  if (item.targetRoute.includes('/products')) {
    return <PackageCheck className="h-[18px] w-[18px] shrink-0 text-[var(--accent-gold)]" aria-hidden="true" />
  }
  return <BookOpenCheck className="h-[18px] w-[18px] shrink-0 text-[var(--accent-gold)]" aria-hidden="true" />
}

export function ActionCenter({ items, totalCount }: ActionCenterProps) {
  const visibleItems = items.slice(0, 5)

  return (
    <Card id="action-center" padding="md" featured className="flex h-full flex-col">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5 min-w-0">
          <ClipboardCheck
            className="mt-0.5 h-5 w-5 shrink-0 text-[var(--accent-gold)]"
            aria-hidden="true"
          />
          <div className="min-w-0">
            <h2 className="text-[18px] font-semibold leading-snug text-[var(--text-primary)]">
              Công việc cần xử lý
            </h2>
            <p className="mt-0.5 text-xs text-[var(--text-muted)]">
              Ưu tiên những tác vụ cần bạn quyết định hoặc theo dõi.
            </p>
          </div>
        </div>
        {totalCount > 5 ? (
          <Link
            to="/studio/sessions"
            className="inline-flex min-h-9 shrink-0 items-center rounded-[8px] px-2.5 py-1.5 text-xs font-semibold text-[var(--accent-gold)] hover:bg-[var(--bg-subtle)] underline-offset-4 hover:underline"
          >
            Xem tất cả ({totalCount})
          </Link>
        ) : null}
      </div>

      <div className="mt-4 flex-1">
        {visibleItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-[10px] border border-dashed border-[var(--border-strong)] bg-[var(--bg-subtle)]/60 px-4 py-8 text-center">
            <CheckCircle2
              className="h-8 w-8 text-[var(--status-success-fg)]"
              aria-hidden="true"
            />
            <p className="mt-2 text-sm font-semibold text-[var(--text-primary)]">
              Không có tác vụ nào đang chờ bạn
            </p>
            <p className="mt-1 text-xs text-[var(--text-muted)]">
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
                  <div className="flex min-w-0 flex-1 items-start gap-3">
                    <div className="mt-0.5">
                      <ActionItemIcon item={item} />
                    </div>
                    <div className="min-w-0 flex-1 space-y-1">
                      <p className="text-sm font-semibold leading-snug text-[var(--text-primary)] group-hover:text-[var(--accent-gold)] transition-colors">
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
                  </div>

                  <div className="flex shrink-0 items-center justify-between gap-2 sm:justify-end">
                    <StatusBadge
                      label={item.statusLabel}
                      tone={item.statusTone}
                      subtle={item.statusTone === 'info' || item.statusTone === 'neutral'}
                      className="whitespace-nowrap"
                    />
                    <ChevronRight
                      className="h-4 w-4 text-[var(--text-muted)] transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-[var(--accent-gold)]"
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
