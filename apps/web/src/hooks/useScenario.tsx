import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import type { UserRole } from '@/types/auth'
import { MOCK_SCENARIO_OPTIONS, type MockScenarioKey } from '@/types/scenario'

interface ScenarioContextValue {
  scenario: MockScenarioKey
  role: UserRole
  setScenario: (key: MockScenarioKey) => void
  setRole: (role: UserRole) => void
  /* Chỉ bật công cụ mô phỏng/Dev Inspector khi ?devTools=1 hoặc bấm Ctrl+Shift+D */
  isDevToolsVisible: boolean
  toggleDevTools: () => void
}

const ScenarioContext = createContext<ScenarioContextValue | null>(null)
const VALID_SCENARIOS = new Set<string>(MOCK_SCENARIO_OPTIONS.map((o) => o.key))

function readInitialScenario(): MockScenarioKey {
  if (typeof window === 'undefined') return 'happy-path'
  const param = new URLSearchParams(window.location.search).get('scenario')
  if (param && VALID_SCENARIOS.has(param)) return param as MockScenarioKey
  return 'happy-path'
}

function readInitialRole(): UserRole {
  if (typeof window === 'undefined') return 'OWNER'
  const param = new URLSearchParams(window.location.search).get('role')?.toUpperCase()
  if (param === 'OPERATOR' || param === 'OWNER') return param
  return 'OWNER'
}

/* Chỉ cho phép bật công cụ mô phỏng trên môi trường dev/localhost hoặc khi cờ env được bật chủ động (chặn bật bằng query ở domain production) */
function isDevInspectorAllowed(): boolean {
  if (typeof window === 'undefined') return false
  if (import.meta.env.DEV || import.meta.env.VITE_ENABLE_MOCK_SWITCHER === 'true') {
    return true
  }
  const host = window.location.hostname
  return host === 'localhost' || host === '127.0.0.1'
}

function readDevToolsVisible(): boolean {
  if (!isDevInspectorAllowed()) return false
  const params = new URLSearchParams(window.location.search)
  const hide = params.get('hideDevBar')
  if (hide === '1' || hide === 'true') return false
  const show = params.get('devTools')
  if (show === '1' || show === 'true') return true
  return false
}

export function ScenarioProvider({ children }: { children: ReactNode }) {
  const [scenario, setScenario] = useState<MockScenarioKey>(readInitialScenario)
  const [role, setRole] = useState<UserRole>(readInitialRole)
  const [isDevToolsVisible, setIsDevToolsVisible] = useState<boolean>(readDevToolsVisible)

  useEffect(() => {
    window.__HOSTRA_MOCK_SCENARIO__ = scenario
    window.__HOSTRA_MOCK_ROLE__ = role
  }, [scenario, role])

  /* Phím tắt Ctrl+Shift+D chỉ hoạt động khi môi trường cho phép Dev Inspector (khóa trên domain production thật) */
  useEffect(() => {
    if (!isDevInspectorAllowed()) return
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'd') {
        e.preventDefault()
        setIsDevToolsVisible((prev) => !prev)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <ScenarioContext.Provider
      value={{
        scenario,
        role,
        setScenario,
        setRole,
        isDevToolsVisible,
        toggleDevTools: () => setIsDevToolsVisible((prev) => !prev),
      }}
    >
      {children}
    </ScenarioContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useScenario(): ScenarioContextValue {
  const ctx = useContext(ScenarioContext)
  if (!ctx) throw new Error('useScenario must be used inside ScenarioProvider')
  return ctx
}

declare global {
  interface Window {
    __HOSTRA_MOCK_SCENARIO__?: MockScenarioKey
    __HOSTRA_MOCK_ROLE__?: UserRole
  }
}
