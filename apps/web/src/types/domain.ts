/** Canonical HOSTRA domain states & shared entities (aligned with Solution Architecture v1.2 & Frontend DECISIONS.md) */

export type SessionLifecycle =
  | 'CREATED'
  | 'PREPARING'
  | 'READY'
  | 'STARTING'
  | 'LIVE'
  | 'STOPPING'
  | 'STOPPED'
  | 'FAILED'
  | 'CANCELLED'

export type AiExecutionState =
  | 'ACTIVE'
  | 'PAUSE_REQUESTED'
  | 'PAUSED'
  | 'RESUMING'
  | 'BLOCKED'

export type MediaHealthState = 'HEALTHY' | 'DEGRADED' | 'FAILED'

export type DialogueSubstate =
  | 'PLAYING_SCRIPT'
  | 'INTERRUPT_PENDING'
  | 'ANSWERING_COMMENT'
  | 'RESUMING'
  | 'IDLE'

export type CommandLifecycle = 'REQUESTED' | 'ACCEPTED' | 'APPLIED' | 'REJECTED'

export type OcopVerificationStatus =
  | 'PENDING_REVIEW'
  | 'VERIFIED'
  | 'REJECTED'
  | 'EXPIRED'
  | 'REVOKED'

export type KnowledgeApprovalStatus =
  | 'DRAFT'
  | 'PENDING_OWNER'
  | 'APPROVED'
  | 'INVALIDATED'
  | 'SUPERSEDED'

export type RightsConsentStatus =
  | 'MISSING'
  | 'PENDING'
  | 'VERIFYING'
  | 'VERIFIED'
  | 'DECLINED'
  | 'EXPIRED'
  | 'REVOKED'

export type PresenterStylePreset = 'CHUYEN_NGHIEP' | 'THAN_THIEN' | 'NANG_DONG'

export type InviteStatus = 'ACTIVE' | 'EXPIRED' | 'EXHAUSTED' | 'REVOKED'

export type ReportStatus = 'PENDING' | 'PARTIAL' | 'READY' | 'FAILED'

export type ConnectionFreshness = 'CONNECTED' | 'STALE' | 'RECONNECTING'

export interface PresenterSummary {
  id: string
  workspaceId: string
  displayName: string
  stylePreset: PresenterStylePreset
  styleLabel: string
  voicePresetLabel: string
  rightsStatus: RightsConsentStatus
  qcStatus: 'PENDING' | 'PASS' | 'FAIL_PARTIAL' | 'FAIL'
  approvalStatus: 'NOT_REVIEWED' | 'APPROVED' | 'REWORK_REQUESTED'
  generationState: 'NOT_STARTED' | 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED'
  activePackVersion: string
  updatedAt: string
}

export interface ProductSkuSummary {
  skuId: string
  skuCode: string
  workspaceId: string
  name: string
  category: string
  priceVnd: number
  packSpec: string
  origin: string
  ocopStatus: OcopVerificationStatus
  ocopStars?: number
  knowledgeStatus: KnowledgeApprovalStatus
  sessionEligible: boolean
  updatedAt: string
}

export interface SessionSummary {
  id: string
  code: string
  workspaceId: string
  title: string
  lifecycle: SessionLifecycle
  aiState: AiExecutionState
  mediaHealth: MediaHealthState
  presenterId: string
  presenterName: string
  skuCount: number
  activeSkuName?: string
  assignedOperatorIds: string[]
  startedAt?: string
  stoppedAt?: string
  updatedAt: string
  revision: number
  epoch: number
  fallbackDescription?: string
}
