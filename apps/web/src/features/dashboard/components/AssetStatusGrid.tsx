import { Link } from 'react-router-dom'
import {
  ArrowUpRight,
  BookOpenCheck,
  PackageCheck,
  Radio,
  Sparkles,
} from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatTwoDigits } from '@/lib/format'
import type { DashboardAssetCardItem } from '@/features/dashboard/types/dashboard.types'

const ASSET_ICONS = {
  presenter: Sparkles,
  products: PackageCheck,
  knowledge: BookOpenCheck,
  sessions: Radio,
}

export function AssetStatusGrid({ items }: { items: DashboardAssetCardItem[] }) {
  return (
    <section aria-label="Tài nguyên của bạn" className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-base font-bold text-[var(--text-primary)]">
          Tài nguyên của bạn
        </h2>
        <p className="text-xs text-[var(--text-muted)]">
          Trạng thái từng nhóm tài nguyên độc lập với điều kiện khởi chạy phiên
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {items.map((item) => {
          const Icon = ASSET_ICONS[item.id]
          return (
            <Link key={item.id} to={item.targetRoute} className="group block">
              <Card
                padding="md"
                className="h-full transition-colors duration-150 group-hover:border-[var(--border-strong)]"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-[var(--text-secondary)]">
                    <Icon className="h-4 w-4 text-[var(--text-muted)]" aria-hidden="true" />
                    <span>{item.label}</span>
                  </div>
                  <ArrowUpRight
                    className="h-4 w-4 text-[var(--text-muted)] transition-transform duration-150 group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                    aria-hidden="true"
                  />
                </div>

                <div className="mt-3 flex items-baseline gap-2.5">
                  <span className="text-2xl font-bold text-[var(--text-primary)] tabular-nums">
                    {formatTwoDigits(item.count)}
                  </span>
                  <span className="text-xs text-[var(--text-secondary)] truncate">
                    {item.subtitle}
                  </span>
                </div>

                <div className="mt-3">
                  {/* PO-D03: Làm dịu badge ở trạng thái bình thường để ưu tiên cảnh báo và lỗi chặn */}
                  <StatusBadge
                    label={item.statusLabel}
                    tone={item.statusTone}
                    subtle={item.statusTone === 'success' || item.statusTone === 'neutral'}
                  />
                </div>
              </Card>
            </Link>
          )
        })}
      </div>
    </section>
  )
}
