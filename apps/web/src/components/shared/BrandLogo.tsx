import { cn } from '@/lib/cn'

export interface BrandLogoProps {
  collapsed?: boolean
  subtitle?: string
  tone?: 'on-dark' | 'adaptive'
  className?: string
}

export function BrandLogo({
  collapsed = false,
  subtitle = 'MERCHANT STUDIO',
  tone = 'on-dark',
  className,
}: BrandLogoProps) {
  const isOnDark = tone === 'on-dark'

  return (
    <div className={cn('flex items-center gap-2.5 select-none', className)}>
      <img
        src="/heritage/logo.svg"
        alt=""
        aria-hidden="true"
        className="h-9 w-9 shrink-0 object-contain"
      />
      {!collapsed ? (
        <div className="min-w-0 leading-tight">
          <div
            className={cn(
              'text-[18px] font-bold tracking-[0.06em]',
              isOnDark ? 'text-[#f7d7a1]' : 'text-[var(--accent-gold)]',
            )}
          >
            HOSTRA
          </div>
          <div
            className={cn(
              'text-[10px] font-medium tracking-[0.12em]',
              isOnDark ? 'text-[#e6d8c5]' : 'text-[var(--text-muted)]',
            )}
          >
            {subtitle}
          </div>
        </div>
      ) : null}
    </div>
  )
}
