import { Check } from 'lucide-react'
import { cn } from '@/lib/cn'

export interface StepperItem {
  id: string
  label: string
  description?: string
}

export interface StepperProps {
  steps: StepperItem[]
  currentIndex: number
  onSelectStep?: (index: number) => void
  className?: string
}

export function Stepper({
  steps,
  currentIndex,
  onSelectStep,
  className,
}: StepperProps) {
  return (
    <ol
      className={cn(
        'grid grid-cols-2 gap-2 sm:grid-cols-4',
        className,
      )}
    >
      {steps.map((step, index) => {
        const isCurrent = index === currentIndex
        const isCompleted = index < currentIndex
        const isClickable = Boolean(onSelectStep && index <= currentIndex)

        const content = (
          <div
            className={cn(
              'flex items-center gap-2.5 border-b-2 px-1.5 py-2.5 text-left transition-colors',
              isCurrent
                ? 'border-[var(--accent-gold)] text-[var(--accent-gold)]'
                : isCompleted
                  ? 'border-[var(--border-strong)] text-[var(--text-primary)]'
                  : 'border-[var(--border-default)] text-[var(--text-muted)]',
            )}
          >
            <span
              className={cn(
                'flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-bold tabular-nums',
                isCurrent
                  ? '[background:var(--cta-primary-bg)] border-[var(--cta-primary-border)] text-[var(--cta-primary-fg)]'
                  : isCompleted
                    ? 'bg-[var(--status-success-bg)] border-[var(--status-success-border)] text-[var(--status-success-fg)]'
                    : 'bg-[var(--bg-surface)] border-[var(--border-default)] text-[var(--text-muted)]',
              )}
            >
              {isCompleted ? <Check className="h-3.5 w-3.5" aria-hidden="true" /> : index + 1}
            </span>
            <span className="min-w-0 truncate text-xs font-semibold">{step.label}</span>
          </div>
        )

        return (
          <li key={step.id} aria-current={isCurrent ? 'step' : undefined}>
            {isClickable ? (
              <button
                type="button"
                onClick={() => onSelectStep?.(index)}
                className="w-full cursor-pointer rounded-t-[6px] hover:bg-[var(--bg-subtle)]/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]"
              >
                {content}
              </button>
            ) : (
              content
            )}
          </li>
        )
      })}
    </ol>
  )
}
