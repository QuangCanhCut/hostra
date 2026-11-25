import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '@/lib/cn'

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  padding?: 'none' | 'sm' | 'md' | 'lg'
  elevated?: boolean
  featured?: boolean
  children: ReactNode
}

const PADDING_CLASSES = {
  none: '',
  sm: 'p-4',
  md: 'p-5',
  lg: 'p-6',
}

export function Card({
  padding = 'md',
  elevated = false,
  featured = false,
  className,
  children,
  ...rest
}: CardProps) {
  return (
    <div
      className={cn(
        'heritage-card rounded-[var(--radius-card)] border min-w-0',
        featured
          ? 'border-[var(--border-strong)]'
          : 'border-[var(--border-default)]',
        elevated ? 'shadow-[var(--shadow-elevated)]' : 'shadow-[var(--shadow-card)]',
        PADDING_CLASSES[padding],
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  )
}
