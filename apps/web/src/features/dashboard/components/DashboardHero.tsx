import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { Banner } from '@/components/ui/Banner'
import { Button } from '@/components/ui/Button'
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
            <Link to={alert.targetRoute}>
              <Button variant="secondary" size="sm">
                {alert.actionLabel}
              </Button>
            </Link>
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

          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <Link to={hero.targetRoute}>
              <Button
                variant="primary"
                size="md"
                rightIcon={<ArrowRight className="h-4 w-4" />}
              >
                {hero.ctaLabel}
              </Button>
            </Link>

            {hero.secondaryLabel && hero.secondaryRoute ? (
              hero.secondaryRoute.startsWith('#') ? (
                <a href={hero.secondaryRoute}>
                  <Button variant="secondary" size="md">
                    {hero.secondaryLabel}
                  </Button>
                </a>
              ) : (
                <Link to={hero.secondaryRoute}>
                  <Button variant="secondary" size="md">
                    {hero.secondaryLabel}
                  </Button>
                </Link>
              )
            ) : null}
          </div>
        </div>
      </section>
    </div>
  )
}
