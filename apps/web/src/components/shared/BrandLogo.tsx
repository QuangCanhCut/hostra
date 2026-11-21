import { cn } from '@/lib/cn'

export interface BrandLogoProps {
  collapsed?: boolean
  subtitle?: string
  className?: string
}

export function BrandLogo({
  collapsed = false,
  subtitle = 'MERCHANT STUDIO',
  className,
}: BrandLogoProps) {
  return (
    <div className={cn('flex items-center gap-2.5 select-none', className)}>
      <div
        aria-hidden="true"
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] bg-[var(--brand-amber)] text-[var(--brand-navy)] font-bold text-base shadow-xs"
      >
        H
      </div>
      {!collapsed ? (
        <div className="min-w-0 leading-tight">
          <div className="text-sm font-bold tracking-wide text-white">HOSTRA</div>
          <div className="text-[10px] font-medium tracking-[0.12em] text-slate-400">
            {subtitle}
          </div>
        </div>
      ) : null}
    </div>
  )
}
