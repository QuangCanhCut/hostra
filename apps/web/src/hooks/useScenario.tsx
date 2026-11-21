import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import type { UserRole } from '@/types/auth'
import { MOCK_SCENARIO_OPTIONS, type MockScenarioKey } from '@/types/scenario'

interface ScenarioContextValue {
  scenario: MockScenarioKey
  role: UserRole
  setScenario: (key: MockScenarioKey) => void
  setRole: (role: UserRole) => void
  isDevToolsVisible: boolean
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

function readDevToolsVisible(): boolean {
  if (typeof window === 'undefined') return false
  const hide = new URLSearchParams(window.location.search).get('hideDevBar')
  if (hide === '1' || hide === 'true') return false
  return import.meta.env.DEV || import.meta.env.VITE_ENABLE_MOCK_SWITCHER === 'true'
}

export function ScenarioProvider({ children }: { children: ReactNode }) {
  const [scenario, setScenario] = useState<MockScenarioKey>(readInitialScenario)
  const [role, setRole] = useState<UserRole>(readInitialRole)
  const [isDevToolsVisible] = useState<boolean>(readDevToolsVisible)

  useEffect(() => {
    window.__HOSTRA_MOCK_SCENARIO__ = scenario
    window.__HOSTRA_MOCK_ROLE__ = role
  }, [scenario, role])

  return (
    <ScenarioContext.Provider
      value={{ scenario, role, setScenario, setRole, isDevToolsVisible }}
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
