import { useState } from 'react'
import { RotateCcw, SlidersHorizontal, X } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useScenario } from '@/hooks/useScenario'
import { MOCK_SCENARIO_OPTIONS, type MockScenarioKey } from '@/types/scenario'
import type { UserRole } from '@/types/auth'

export function DevScenarioBar() {
  const { scenario, role, setScenario, setRole, isDevToolsVisible } = useScenario()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)

  if (!isDevToolsVisible) return null

  const handleReset = async () => {
    await fetch('/api/mock/v1/reset', {
      method: 'POST',
      headers: {
        'X-Hostra-Scenario': scenario,
        'X-Hostra-Role': role,
      },
    })
    await queryClient.invalidateQueries()
  }

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {!open ? (
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="Mở bảng chọn kịch bản mô phỏng"
          className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--border-strong)] bg-[var(--brand-navy)] px-3.5 text-xs font-medium text-white shadow-[var(--shadow-elevated)] hover:opacity-95 cursor-pointer"
        >
          <SlidersHorizontal className="h-3.5 w-3.5 text-[var(--brand-amber)]" />
          <span>Mock: {role === 'OWNER' ? 'Owner' : 'Operator'}</span>
        </button>
      ) : (
        <div className="w-[320px] rounded-[14px] border border-[var(--border-strong)] bg-[var(--bg-elevated)] p-4 shadow-[var(--shadow-elevated)]">
          <div className="flex items-center justify-between gap-2 pb-3 border-b border-[var(--border-default)]">
            <div>
              <p className="text-xs font-semibold text-[var(--text-primary)]">
                Bảng chọn kịch bản mô phỏng (Dev)
              </p>
              <p className="text-[11px] text-[var(--text-muted)]">
                Chỉ hiển thị ở môi trường kiểm thử nội bộ
              </p>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Đóng bảng chọn kịch bản"
              className="flex h-7 w-7 items-center justify-center rounded-[6px] text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="mt-3 space-y-3">
            <div>
              <label className="block text-[11px] font-medium text-[var(--text-secondary)] mb-1.5">
                Vai trò đang mô phỏng
              </label>
              <div className="grid grid-cols-2 gap-2">
                {(['OWNER', 'OPERATOR'] as UserRole[]).map((item) => {
                  const active = role === item
                  return (
                    <button
                      key={item}
                      type="button"
                      onClick={() => setRole(item)}
                      className={
                        active
                          ? 'h-9 rounded-[8px] bg-[var(--brand-amber)] text-[var(--text-on-amber)] text-xs font-semibold cursor-pointer'
                          : 'h-9 rounded-[8px] border border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-secondary)] text-xs font-medium hover:bg-[var(--bg-subtle)] cursor-pointer'
                      }
                    >
                      {item === 'OWNER' ? 'Chủ sở hữu (Owner)' : 'Vận hành (Operator)'}
                    </button>
                  )
                })}
              </div>
            </div>

            <div>
              <label
                htmlFor="mock-scenario-select"
                className="block text-[11px] font-medium text-[var(--text-secondary)] mb-1.5"
              >
                Kịch bản dữ liệu
              </label>
              <select
                id="mock-scenario-select"
                value={scenario}
                onChange={(e) => setScenario(e.target.value as MockScenarioKey)}
                className="w-full h-9 rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-2.5 text-xs text-[var(--text-primary)]"
              >
                {MOCK_SCENARIO_OPTIONS.map((opt) => (
                  <option key={opt.key} value={opt.key}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="button"
              onClick={handleReset}
              className="flex h-9 w-full items-center justify-center gap-1.5 rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] text-xs font-medium text-[var(--text-primary)] hover:bg-[var(--bg-subtle)] cursor-pointer"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Đặt lại dữ liệu mô phỏng</span>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
