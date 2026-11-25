import { useState } from 'react'
import { cn } from '@/lib/cn'

export type DemoVisualKey =
  | 'prs-linh-01'
  | 'prs-mai-02'
  | 'prs-an-03'
  | 'sku-ml-001'
  | 'sku-ml-002'
  | 'sku-ml-003'
  | 'sku-ml-004'
  | 'sku-ml-005'

const PRESENTER_IMAGES: Record<string, string> = {
  'prs-linh-01': '/demo/presenters/linh.jpg',
  'prs-mai-02': '/demo/presenters/mai.jpg',
  'prs-an-03': '/demo/presenters/an.jpg',
}

const PRESENTER_FALLBACK_BG: Record<string, string> = {
  'prs-linh-01': '#FEF3C7',
  'prs-mai-02': '#DBEAFE',
  'prs-an-03': '#DCFCE7',
}

const PRODUCT_PALETTES: Record<
  string,
  { bg: string; jar: string; cap: string; label: string }
> = {
  'sku-ml-001': { bg: '#FFF7ED', jar: '#B45309', cap: '#78350F', label: 'Mứt Mận' },
  'sku-ml-002': { bg: '#FEF9C3', jar: '#D97706', cap: '#92400E', label: 'Mật Ong' },
  'sku-ml-003': { bg: '#ECFDF5', jar: '#15803D', cap: '#14532D', label: 'Trà Thảo Mộc' },
  'sku-ml-004': { bg: '#FEF3C7', jar: '#CA8A04', cap: '#713F12', label: 'Chuối Sấy' },
  'sku-ml-005': { bg: '#F1F5F9', jar: '#475569', cap: '#1E293B', label: 'Măng Khô' },
}

/**
 * Uniform 4:3 photorealistic synthetic AI presenter portrait (zero pillarbox, local static asset).
 */
export function PresenterPortrait({
  presenterId,
  name,
  className,
}: {
  presenterId: string
  name: string
  className?: string
}) {
  const [failed, setFailed] = useState(false)
  const src = PRESENTER_IMAGES[presenterId] ?? PRESENTER_IMAGES['prs-linh-01']
  const fallbackBg = PRESENTER_FALLBACK_BG[presenterId] ?? '#FEF3C7'

  return (
    <div
      className={cn(
        'relative aspect-[4/3] w-full overflow-hidden rounded-[10px] border border-[var(--border-default)]',
        className,
      )}
      style={{ backgroundColor: fallbackBg }}
    >
      {!failed ? (
        <img
          src={src}
          alt={`Ảnh chân dung AI minh họa ${name}`}
          loading="eager"
          onError={() => setFailed(true)}
          className="h-full w-full object-cover object-top"
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center text-sm font-semibold text-slate-700">
          {name}
        </div>
      )}
    </div>
  )
}

/**
 * Clean square product demo illustration (OCOP badge always placed outside thumbnail per v0.4).
 */
export function ProductThumb({
  skuId,
  name,
  className,
}: {
  skuId: string
  name: string
  className?: string
}) {
  const palette = PRODUCT_PALETTES[skuId] ?? PRODUCT_PALETTES['sku-ml-001']

  return (
    <div
      className={cn(
        'flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-[10px] border border-[var(--border-default)] dark:opacity-90',
        className,
      )}
      style={{ backgroundColor: palette.bg }}
      aria-label={`Ảnh sản phẩm ${name}`}
    >
      <svg viewBox="0 0 64 64" className="h-full w-full" role="img" aria-label={name}>
        <rect width="64" height="64" fill={palette.bg} />
        <rect x="20" y="13" width="24" height="7" rx="3" fill={palette.cap} />
        <rect x="16" y="20" width="32" height="32" rx="7" fill={palette.jar} />
        <rect x="21" y="28" width="22" height="14" rx="3" fill="#FFFFFF" opacity="0.92" />
        <rect x="25" y="33" width="14" height="2.5" rx="1.2" fill={palette.cap} />
        <rect x="27" y="37.5" width="10" height="2" rx="1" fill={palette.jar} opacity="0.7" />
      </svg>
    </div>
  )
}
