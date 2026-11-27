import { Moon, Sun } from 'lucide-react'
import { useTheme } from '@/hooks/useTheme'
import { cn } from '@/lib/cn'

export function ThemeToggle({
  className,
  tone = 'adaptive',
}: {
  className?: string
  tone?: 'adaptive' | 'on-dark'
}) {
  const { theme, toggleTheme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isDark ? 'Chuyển sang chế độ sáng' : 'Chuyển sang chế độ tối'}
      title={isDark ? 'Chế độ sáng' : 'Chế độ tối'}
      className={cn(
        'inline-flex h-10 w-10 items-center justify-center rounded-[8px] border transition-colors duration-150 cursor-pointer',
        tone === 'on-dark'
          ? 'border-[#5a4632]/70 bg-[#251d17]/90 text-[#f2c47d] hover:border-[#896641] hover:bg-[#31261e]'
          : 'border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--accent-gold)] hover:border-[var(--border-strong)] hover:bg-[var(--bg-raised)]',
        className,
      )}
    >
      {isDark ? (
        <Sun className="h-4 w-4" aria-hidden="true" />
      ) : (
        <Moon className="h-4 w-4" aria-hidden="true" />
      )}
    </button>
  )
}
