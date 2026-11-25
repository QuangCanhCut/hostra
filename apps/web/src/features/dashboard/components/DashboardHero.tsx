import { ArrowRight, Leaf } from 'lucide-react'
import { Banner } from '@/components/ui/Banner'
import { ButtonLink } from '@/components/ui/Button'
import type {
  DashboardCriticalAlert,
  DashboardHeroAction,
} from '@/features/dashboard/types/dashboard.types'

export interface DashboardHeroProps {
  hero: DashboardHeroAction
  criticalAlerts: DashboardCriticalAlert[]
  workspaceName?: string
}

export function DashboardHero({
  hero,
  criticalAlerts,
  workspaceName,
}: DashboardHeroProps) {
  return (
    <div className="space-y-4">
      {criticalAlerts.map((alert) => (
        <Banner
          key={alert.id}
          severity={alert.severity}
          title={alert.title}
          description={alert.description}
          action={
            <ButtonLink to={alert.targetRoute} variant="secondary" size="sm">
              {alert.actionLabel}
            </ButtonLink>
          }
        />
      ))}

      <section
        aria-label="Hành động ưu tiên tiếp theo"
        className="relative flex min-h-[212px] items-center overflow-hidden rounded-[var(--radius-lg)] border border-[var(--bg-hero-border)] [background:var(--bg-hero)] px-5 py-6 text-[#f5ebdd] shadow-[var(--shadow-card)] sm:px-8 sm:py-7"
      >
        {/* Ảnh trang trí vùng cao bên phải — chỉ dùng làm bối cảnh thị giác, không phải chứng từ sản phẩm */}
        <div
          aria-hidden="true"
          className="pointer-events-none select-none absolute inset-0 sm:left-[42%]"
        >
          <img
            src="/heritage/hero.webp"
            alt=""
            className="h-full w-full object-cover object-center"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-[#23190f]/95 via-[#23190f]/80 to-[#23190f]/55 sm:from-[#26190d] sm:via-[#26190d]/45 sm:to-transparent" />
        </div>

        <div className="relative z-10 max-w-2xl space-y-2">
          {workspaceName ? (
            <div className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.13em] text-[#f2c47d]">
              <Leaf className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              <span>{workspaceName}</span>
            </div>
          ) : null}

          <h2 className="font-display text-[24px] font-bold leading-[1.16] tracking-[-0.02em] text-[#f5ebdd] sm:text-[31px]">
            {hero.headline}
          </h2>

          <p className="max-w-xl text-sm leading-relaxed text-[#f2e4d4]/90">
            {hero.summary}
          </p>

          {/* Dùng ButtonLink / anchor tạo kiểu nút trực tiếp để tránh lồng <button> trong <a> (UX-04) */}
          <div className="flex flex-wrap items-center gap-2.5 pt-3">
            <ButtonLink
              to={hero.targetRoute}
              variant="primary"
              size="md"
              rightIcon={<ArrowRight className="h-4 w-4" />}
            >
              {hero.ctaLabel}
            </ButtonLink>

            {hero.secondaryLabel && hero.secondaryRoute ? (
              hero.secondaryRoute.startsWith('#') ? (
                <a
                  href={hero.secondaryRoute}
                  className="inline-flex min-h-10 items-center justify-center gap-2 whitespace-nowrap rounded-[8px] border border-[#ae8756] bg-[#21160c]/45 px-4 text-sm font-semibold text-[#f5ebdd] transition-colors duration-150 hover:bg-[#3a2819]/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#f2c47d] focus-visible:ring-offset-1 focus-visible:ring-offset-[#23190f]"
                >
                  {hero.secondaryLabel}
                </a>
              ) : (
                <ButtonLink
                  to={hero.secondaryRoute}
                  variant="secondary"
                  size="md"
                  className="border-[#ae8756] bg-[#21160c]/45 text-[#f5ebdd] hover:bg-[#3a2819]/80"
                >
                  {hero.secondaryLabel}
                </ButtonLink>
              )
            ) : null}
          </div>
        </div>
      </section>
    </div>
  )
}
