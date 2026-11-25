import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link, type LinkProps } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/cn'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'destructive'
export type ButtonSize = 'sm' | 'md' | 'lg'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  leftIcon?: ReactNode
  rightIcon?: ReactNode
}

export interface ButtonLinkProps extends Omit<LinkProps, 'children'> {
  variant?: ButtonVariant
  size?: ButtonSize
  leftIcon?: ReactNode
  rightIcon?: ReactNode
  children: ReactNode
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    '[background:var(--cta-primary-bg)] hover:[background:var(--cta-primary-bg-hover)] text-[var(--cta-primary-fg)] font-semibold border border-[var(--cta-primary-border)] shadow-[var(--cta-primary-shadow)]',
  secondary:
    'bg-transparent text-[var(--text-primary)] hover:bg-[var(--bg-raised)] font-semibold border border-[var(--border-strong)]',
  ghost:
    'bg-transparent text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)] font-medium border border-transparent',
  destructive:
    'bg-[var(--brand-danger)] text-white hover:bg-[var(--brand-danger-hover)] font-semibold border border-[var(--brand-danger-border)]',
}

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: 'min-h-9 px-3 text-xs rounded-[8px] gap-1.5',
  md: 'min-h-10 px-4 text-sm rounded-[8px] gap-2',
  lg: 'min-h-11 px-5 text-sm rounded-[10px] gap-2',
}

/* Lớp nền chung giúp Button và ButtonLink đồng nhất hoàn toàn về kích thước và vòng focus */
const BASE_BUTTON_CLASSES =
  'inline-flex items-center justify-center whitespace-nowrap transition-all duration-150 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)] focus-visible:ring-offset-1 focus-visible:ring-offset-[var(--bg-canvas)]'

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled,
  leftIcon,
  rightIcon,
  className,
  children,
  type = 'button',
  ...rest
}: ButtonProps) {
  const isDisabled = Boolean(disabled || loading)

  return (
    <button
      type={type}
      disabled={isDisabled}
      className={cn(
        BASE_BUTTON_CLASSES,
        'disabled:opacity-50 disabled:cursor-not-allowed',
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        className,
      )}
      {...rest}
    >
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin shrink-0" aria-hidden="true" />
      ) : (
        leftIcon && <span className="shrink-0">{leftIcon}</span>
      )}
      <span>{children}</span>
      {!loading && rightIcon ? <span className="shrink-0">{rightIcon}</span> : null}
    </button>
  )
}

/* Liên kết hiển thị dạng nút để tránh lồng <button> bên trong <a> (đạt chuẩn HTML5 & WCAG) */
export function ButtonLink({
  variant = 'secondary',
  size = 'md',
  leftIcon,
  rightIcon,
  className,
  children,
  ...rest
}: ButtonLinkProps) {
  return (
    <Link
      className={cn(
        BASE_BUTTON_CLASSES,
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        className,
      )}
      {...rest}
    >
      {leftIcon ? <span className="shrink-0">{leftIcon}</span> : null}
      <span>{children}</span>
      {rightIcon ? <span className="shrink-0">{rightIcon}</span> : null}
    </Link>
  )
}
