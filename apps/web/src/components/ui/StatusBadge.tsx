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
  className,
}: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium leading-5',
        TONE_CLASSES[tone],
        className,
      )}
    >
      {showIcon ? <ToneIcon tone={tone} pulse={pulse} /> : null}
      <span>{label}</span>
    </span>
  )
}
