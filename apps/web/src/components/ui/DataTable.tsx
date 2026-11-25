import type { ReactNode } from 'react'
import { Card } from '@/components/ui/Card'
import { cn } from '@/lib/cn'

export interface DataTableProps {
  children: ReactNode
  className?: string
  featured?: boolean
}

export function DataTable({ children, className, featured = false }: DataTableProps) {
  return (
    <Card padding="none" featured={featured} className={cn('overflow-hidden', className)}>
      <div className="overflow-x-auto">{children}</div>
    </Card>
  )
}

export const TABLE_HEAD_ROW_CLASS =
  'border-b border-[var(--border-default)] bg-[var(--bg-surface)] text-[11px] font-semibold uppercase tracking-[0.06em] text-[var(--text-muted)]'

export const TABLE_BODY_CLASS = 'divide-y divide-[var(--border-default)]'

export const TABLE_ROW_HOVER_CLASS =
  'transition-colors duration-150 hover:bg-[var(--bg-raised)]/65'
