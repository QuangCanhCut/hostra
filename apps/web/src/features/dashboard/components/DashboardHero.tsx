import { ArrowRight } from 'lucide-react'
import { Banner } from '@/components/ui/Banner'
import { ButtonLink } from '@/components/ui/Button'
import type {
  DashboardCriticalAlert,
  DashboardHeroAction,
} from '@/features/dashboard/types/dashboard.types'

export interface DashboardHeroProps {
  hero: DashboardHeroAction
  criticalAlerts: DashboardCriticalAlert[]
}

export function DashboardHero({ hero, criticalAlerts }: DashboardHeroProps) {
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
        className="rounded-[14px] border border-[var(--bg-hero-border)] bg-[var(--bg-hero)] p-5 sm:p-6"
      >
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-1.5 max-w-2xl">
            <h2 className="text-lg font-bold text-[var(--text-primary)] sm:text-xl">
              {hero.headline}
            </h2>
            <p className="text-sm text-[var(--text-secondary)]">{hero.summary}</p>
          </div>

          {/* Dùng ButtonLink / anchor tạo kiểu nút trực tiếp để tránh lồng <button> trong <a> (UX-04) */}
          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
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
                  className="inline-flex min-h-10 items-center justify-center gap-2 whitespace-nowrap rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-4 text-sm font-medium text-[var(--text-primary)] transition-colors duration-150 hover:bg-[var(--bg-subtle)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)] focus-visible:ring-offset-1 focus-visible:ring-offset-[var(--bg-canvas)]"
                >
                  {hero.secondaryLabel}
                </a>
              ) : (
                <ButtonLink to={hero.secondaryRoute} variant="secondary" size="md">
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
