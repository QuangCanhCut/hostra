import { Link } from 'react-router-dom'
import {
  ArrowUpRight,
  BookOpenCheck,
  Leaf,
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

/* Ảnh WebP trang trí góc phải thẻ tài nguyên (chỉ mang tính thẩm mỹ, không phải bằng chứng nghiệp vụ) */
const ASSET_ART: Record<DashboardAssetCardItem['id'], string> = {
  presenter: '/heritage/microphone.webp',
  products: '/heritage/plums.webp',
  knowledge: '/heritage/knowledge-book.webp',
  sessions: '/heritage/camera.webp',
}

export function AssetStatusGrid({ items }: { items: DashboardAssetCardItem[] }) {
  return (
    <section aria-label="Tài nguyên của bạn" className="space-y-3.5">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
        <div className="flex items-center gap-2">
          <Leaf
            className="h-4 w-4 shrink-0 text-[var(--accent-gold)]"
            aria-hidden="true"
          />
          <h2 className="font-display text-[21px] font-bold leading-snug text-[var(--text-primary)] sm:text-[23px]">
            Tài nguyên của bạn
          </h2>
        </div>
        <p className="text-xs text-[var(--text-muted)]">
          Trạng thái từng nhóm tài nguyên độc lập với điều kiện khởi chạy phiên
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {items.map((item) => {
          const Icon = ASSET_ICONS[item.id]
          const artSrc = ASSET_ART[item.id]
          return (
            <Link key={item.id} to={item.targetRoute} className="group block">
              <Card
                padding="md"
                featured
                className="relative h-full min-h-[146px] overflow-hidden transition-colors duration-150 group-hover:border-[var(--accent-gold)]"
              >
                <img
                  src={artSrc}
                  alt=""
                  aria-hidden="true"
                  loading="lazy"
                  className="pointer-events-none select-none absolute right-0 bottom-0 h-[76%] w-[44%] object-cover opacity-85 heritage-resource-mask transition-opacity duration-200 group-hover:opacity-95"
                />

                <div className="relative z-10 flex h-full flex-col justify-between gap-2.5">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 text-xs font-semibold text-[var(--text-primary)]">
                      <Icon
                        className="h-4 w-4 shrink-0 text-[var(--accent-gold)]"
                        aria-hidden="true"
                      />
                      <span>{item.label}</span>
                    </div>
                    <ArrowUpRight
                      className="h-4 w-4 shrink-0 text-[var(--text-muted)] transition-transform duration-150 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-[var(--accent-gold)]"
                      aria-hidden="true"
                    />
                  </div>

                  <div className="max-w-[74%] space-y-1">
                    <div className="text-[32px] font-semibold leading-none text-[var(--text-primary)] tabular-nums">
                      {formatTwoDigits(item.count)}
                    </div>
                    <p className="text-xs text-[var(--text-secondary)] truncate">
                      {item.subtitle}
                    </p>
                  </div>

                  <div>
                    {/* PO-D03: Làm dịu badge ở trạng thái bình thường để ưu tiên cảnh báo và lỗi chặn */}
                    <StatusBadge
                      label={item.statusLabel}
                      tone={item.statusTone}
                      subtle={item.statusTone === 'success' || item.statusTone === 'neutral'}
                    />
                  </div>
                </div>
              </Card>
            </Link>
          )
        })}
      </div>
    </section>
  )
}
