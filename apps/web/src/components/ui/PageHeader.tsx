import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

export interface PageHeaderProps {
  title: string
  subtitle?: string
  leading?: ReactNode
  actions?: ReactNode
  className?: string
}

export function PageHeader({
  title,
  subtitle,
  leading,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        'flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between',
        className,
      )}
    >
      <div className="flex items-start gap-3 min-w-0">
        {leading ? <div className="mt-0.5 shrink-0">{leading}</div> : null}
        <div className="min-w-0">
          <h1 className="font-display text-[26px] font-bold leading-[1.16] tracking-[-0.02em] text-[var(--text-primary)] sm:text-[32px]">
            {title}
          </h1>
          {subtitle ? (
            <p className="mt-1 text-sm text-[var(--text-muted)]">{subtitle}</p>
          ) : null}
        </div>
      </div>

      {actions ? (
        <div className="flex flex-wrap items-center gap-2.5 shrink-0">{actions}</div>
      ) : null}
    </div>
  )
}
