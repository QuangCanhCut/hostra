import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Info,
  Radio,
  XCircle,
} from 'lucide-react'
import { cn } from '@/lib/cn'
import type { BadgeTone } from '@/lib/status-copy'

export interface StatusBadgeProps {
  label: string
  tone: BadgeTone
  pulse?: boolean
  showIcon?: boolean
  /* Biến thể nhẹ giảm mật độ màu trên các trang nhiều trạng thái */
  subtle?: boolean
  className?: string
}

const TONE_CLASSES: Record<BadgeTone, string> = {
  success:
    'bg-[var(--status-success-bg)] text-[var(--status-success-fg)] border-[var(--status-success-border)]',
  warning:
    'bg-[var(--status-warning-bg)] text-[var(--status-warning-fg)] border-[var(--status-warning-border)]',
  danger:
    'bg-[var(--status-danger-bg)] text-[var(--status-danger-fg)] border-[var(--status-danger-border)]',
  info: 'bg-[var(--status-info-bg)] text-[var(--status-info-fg)] border-[var(--status-info-border)]',
  neutral:
    'bg-[var(--status-neutral-bg)] text-[var(--status-neutral-fg)] border-[var(--status-neutral-border)]',
}

const SUBTLE_TONE_CLASSES: Record<BadgeTone, string> = {
  success:
    'bg-[var(--status-success-bg)]/70 text-[var(--status-success-fg)] border-[var(--status-success-border)]',
  warning:
    'bg-[var(--status-warning-bg)]/70 text-[var(--status-warning-fg)] border-[var(--status-warning-border)]',
  danger:
    'bg-[var(--status-danger-bg)]/70 text-[var(--status-danger-fg)] border-[var(--status-danger-border)]',
  info: 'bg-[var(--status-info-bg)]/70 text-[var(--status-info-fg)] border-[var(--status-info-border)]',
  neutral:
    'bg-[var(--bg-subtle)] text-[var(--text-muted)] border-[var(--border-default)]',
}

function ToneIcon({ tone, pulse }: { tone: BadgeTone; pulse?: boolean }) {
  if (pulse) {
    return <Radio className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
  }
  switch (tone) {
    case 'success':
      return <CheckCircle2 className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
    case 'warning':
      return <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
    case 'danger':
      return <XCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
    case 'info':
      return <Info className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
    default:
      return <Clock className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
  }
}

export function StatusBadge({
  label,
  tone,
  pulse = false,
  showIcon = true,
  subtle = false,
  className,
}: StatusBadgeProps) {
  return (
    <span
      className={cn(
        /* Luôn giữ 1 dòng không bóp méo chữ trên thẻ hẹp */
        'inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-[11px] font-semibold leading-5 tracking-[0.01em]',
        subtle ? SUBTLE_TONE_CLASSES[tone] : TONE_CLASSES[tone],
        className,
      )}
    >
      {showIcon ? <ToneIcon tone={tone} pulse={pulse} /> : null}
      <span>{label}</span>
    </span>
  )
}
