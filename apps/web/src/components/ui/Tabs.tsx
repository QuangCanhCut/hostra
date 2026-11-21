import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

export interface TabItem<T extends string> {
  id: T
  label: string
  count?: number
  badge?: ReactNode
}

export interface TabsProps<T extends string> {
  items: Array<TabItem<T>>
  activeId: T
  onChange: (id: T) => void
  ariaLabel?: string
  className?: string
}

export function Tabs<T extends string>({
  items,
  activeId,
  onChange,
  ariaLabel = 'Điều hướng tab',
  className,
}: TabsProps<T>) {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={cn(
        'flex items-center gap-1 overflow-x-auto border-b border-[var(--border-default)]',
        className,
      )}
    >
      {items.map((item) => {
        const isActive = item.id === activeId
        return (
          <button
            key={item.id}
            role="tab"
            type="button"
            aria-selected={isActive}
            onClick={() => onChange(item.id)}
            className={cn(
              'relative inline-flex min-h-[44px] shrink-0 items-center gap-2 px-3.5 py-2 text-sm font-medium transition-colors cursor-pointer',
              isActive
                ? 'text-[var(--text-primary)] font-semibold'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]',
            )}
          >
            <span>{item.label}</span>
            {typeof item.count === 'number' ? (
              <span
                className={cn(
                  'rounded-full px-2 py-0.5 text-xs tabular-nums',
                  isActive
                    ? 'bg-[var(--brand-amber)] text-[var(--text-on-amber)] font-semibold'
                    : 'bg-[var(--bg-subtle)] text-[var(--text-secondary)]',
                )}
              >
                {item.count}
              </span>
            ) : null}
            {item.badge}
            {isActive ? (
              <span
                aria-hidden="true"
                className="absolute inset-x-0 bottom-0 h-0.5 bg-[var(--brand-amber)]"
              />
            ) : null}
          </button>
        )
      })}
    </div>
  )
}
