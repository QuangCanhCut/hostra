import type { ReactNode } from 'react'
import { Card } from '@/components/ui/Card'
import { cn } from '@/lib/cn'

export interface EmptyStateProps {
  icon: ReactNode
  title: string
  description: string
  action?: ReactNode
  tone?: 'neutral' | 'danger' | 'warning'
  className?: string
}

const ICON_BG = {
  neutral: 'bg-[var(--bg-subtle)] text-[var(--text-secondary)]',
  danger: 'bg-[var(--status-danger-bg)] text-[var(--status-danger-fg)]',
  warning: 'bg-[var(--status-warning-bg)] text-[var(--status-warning-fg)]',
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  tone = 'neutral',
  className,
}: EmptyStateProps) {
  return (
    <Card
      padding="lg"
      className={cn('flex flex-col items-center justify-center text-center', className)}
    >
      <div
        className={cn(
          'mb-4 flex h-12 w-12 items-center justify-center rounded-full',
          ICON_BG[tone],
        )}
      >
        {icon}
      </div>
      <h2 className="text-base font-semibold text-[var(--text-primary)]">{title}</h2>
      <p className="mt-1.5 max-w-md text-sm text-[var(--text-secondary)]">
        {description}
      </p>
      {action ? <div className="mt-5">{action}</div> : null}
    </Card>
  )
}
