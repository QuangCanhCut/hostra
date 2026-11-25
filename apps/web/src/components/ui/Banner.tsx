import type { ReactNode } from 'react'
import { AlertOctagon, AlertTriangle, CheckCircle2, Info } from 'lucide-react'
import { cn } from '@/lib/cn'

export interface BannerProps {
  severity: 'danger' | 'warning' | 'info' | 'success'
  title: string
  description: string
  action?: ReactNode
  className?: string
}

const SEVERITY_STYLES = {
  danger:
    'bg-[var(--status-danger-bg)] text-[var(--status-danger-fg)] border-[var(--status-danger-border)]',
  warning:
    'bg-[var(--status-warning-bg)] text-[var(--status-warning-fg)] border-[var(--status-warning-border)]',
  info: 'bg-[var(--status-info-bg)] text-[var(--status-info-fg)] border-[var(--status-info-border)]',
  success:
    'bg-[var(--status-success-bg)] text-[var(--status-success-fg)] border-[var(--status-success-border)]',
}

export function Banner({
  severity,
  title,
  description,
  action,
  className,
}: BannerProps) {
  const Icon =
    severity === 'danger'
      ? AlertOctagon
      : severity === 'warning'
        ? AlertTriangle
        : severity === 'success'
          ? CheckCircle2
          : Info

  return (
    <div
      role={severity === 'danger' ? 'alert' : 'status'}
      className={cn(
        'flex flex-col gap-3 rounded-[var(--radius-card)] border px-4 py-3.5 sm:flex-row sm:items-center sm:justify-between',
        SEVERITY_STYLES[severity],
        className,
      )}
    >
      <div className="flex items-start gap-3">
        <Icon className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        <div className="space-y-0.5">
          <p className="text-sm font-semibold">{title}</p>
          <p className="text-xs opacity-90 sm:text-sm">{description}</p>
        </div>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  )
}
