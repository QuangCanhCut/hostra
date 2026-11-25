import type { ConnectionFreshness, SessionSummary } from '@/types/domain'
import type { BadgeTone } from '@/lib/status-copy'

export type ActionPriority = 'CRITICAL' | 'BLOCKER' | 'APPROVAL' | 'SETUP' | 'INFO'

export interface DashboardActionItem {
  id: string
  priority: ActionPriority
  title: string
  resourceLabel: string
  statusLabel: string
  statusTone: BadgeTone
  targetRoute: string
  actionableByViewer: boolean
  waitingRoleLabel?: string
}

export interface DashboardCriticalAlert {
  id: string
  severity: 'danger' | 'warning' | 'info'
  title: string
  description: string
  actionLabel: string
  targetRoute: string
}

export interface DashboardHeroAction {
  headline: string
  summary: string
  ctaLabel: string
  targetRoute: string
  secondaryLabel?: string
  secondaryRoute?: string
}

export interface DashboardAssetCardItem {
  id: 'presenter' | 'products' | 'knowledge' | 'sessions'
  label: string
  count: number
  subtitle: string
  statusLabel: string
  statusTone: BadgeTone
  targetRoute: string
}

export interface DashboardSnapshot {
  workspaceName: string
  snapshotRevision: number
  generatedAt: string
  freshness: ConnectionFreshness
  hero: DashboardHeroAction
  criticalAlerts: DashboardCriticalAlert[]
  actionItems: DashboardActionItem[]
  totalActionCount: number
  featuredSession: SessionSummary | null
  assetCards: DashboardAssetCardItem[]
  recentSessions: SessionSummary[]
}
