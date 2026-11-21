import { useEffect, type ReactNode } from 'react'
import { X } from 'lucide-react'

export interface DrawerProps {
  open: boolean
  onClose: () => void
  title: string
  subtitle?: string
  children: ReactNode
}

export function Drawer({ open, onClose, title, subtitle, children }: DrawerProps) {
  useEffect(() => {
    if (!open) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div
        className="fixed inset-0 bg-[var(--overlay-scrim)]"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative z-10 flex h-full w-full max-w-lg flex-col border-l border-[var(--border-strong)] bg-[var(--bg-elevated)] shadow-[var(--shadow-elevated)]">
        <div className="flex items-start justify-between gap-3 border-b border-[var(--border-default)] px-5 py-4">
          <div className="min-w-0">
            <h2 className="text-base font-bold text-[var(--text-primary)] truncate">
              {title}
            </h2>
            {subtitle ? (
              <p className="mt-0.5 text-xs text-[var(--text-secondary)] truncate">
                {subtitle}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng bảng chi tiết"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[8px] text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-5">{children}</div>
      </div>
    </div>
  )
}
