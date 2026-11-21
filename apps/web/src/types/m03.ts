import type {
  AiExecutionState,
  CommandLifecycle,
  ConnectionFreshness,
  DialogueSubstate,
  InviteStatus,
  MediaHealthState,
  ReportStatus,
  SessionLifecycle,
} from '@/types/domain'
import type { UserRole } from '@/types/auth'

/* ---------- M03-B: Members & Permissions ---------- */

export type MemberStatus = 'ACTIVE' | 'SUSPENDED' | 'REMOVED'
export type OperatorInviteStatus = 'PENDING' | 'ACCEPTED' | 'EXPIRED' | 'REVOKED' | 'IDENTITY_MISMATCH'

export interface WorkspaceMember {
  id: string
  displayName: string
  email: string
  initials: string
  role: UserRole
  roleLabel: string
  status: MemberStatus
  assignedSessionIds: string[]
  revision: number
  joinedAt: string
}

export interface OperatorInvitation {
  id: string
  email: string
  status: OperatorInviteStatus
  expiresAt: string
  invitedBy: string
  createdAt: string
}

export interface AccessAuditEvent {
  id: string
  occurredAt: string
  actorName: string
  action: string
  targetLabel: string
  decision: 'APPLIED' | 'REJECTED'
  reason: string
  sessionId?: string
}

/* ---------- M03-A: Live Control Room ---------- */

export type PublisherState = 'CONNECTED' | 'DEGRADED' | 'DISCONNECTED'

export type SpeechTurnPhase =
  | 'PLANNING'
  | 'VERIFYING'
  | 'PREPARING_AUDIO'
  | 'LIP_SYNC'
  | 'READY'
  | 'COMMITTED'
  | 'PLAYING'
  | 'PLAYBACK_COMPLETED'
  | 'CANCELLED'

export type RuntimeCommandType =
  | 'PAUSE_AI'
  | 'RESUME_AI'
  | 'SWITCH_SKU'
  | 'PRIORITIZE_COMMENT'
  | 'SKIP_PENDING'
  | 'STOP'
  | 'EMERGENCY_STOP'

export interface LiveCommentItem {
  id: string
  sessionId: string
  viewerId: string
  nickname: string
  body: string
  receivedAt: string
  referencedSkuCode?: string
  moderationStatus: 'ELIGIBLE' | 'MODERATION_BLOCKED' | 'SPAM'
  queueStatus: 'QUEUED' | 'PRIORITIZED' | 'COMMITTED' | 'PLAYED' | 'SKIPPED'
  priorityScore: number
  ttlSeconds: number
}

export interface SpeechTurnRecord {
  turnId: string
  commentId?: string
  skuCode?: string
  safeSummary: string
  sourceRef: string
  phase: SpeechTurnPhase
  playbackAckId?: string
  updatedAt: string
}

export interface PendingSkuSwitch {
  commandId: string
  targetSkuId: string
  targetSkuCode: string
  targetSkuName: string
  actorName: string
  status: CommandLifecycle
  requestedAt: string
}

export interface RuntimeCommandRecord {
  commandId: string
  type: RuntimeCommandType
  actorId: string
  actorName: string
  expectedRevision: number
  sessionEpoch: number
  status: CommandLifecycle
  reason: string
  requestedAt: string
}

export interface ControlRoomSnapshot {
  sessionId: string
  sessionCode: string
  sessionTitle: string
  revision: number
  epoch: number
  lifecycle: SessionLifecycle
  aiState: AiExecutionState
  mediaHealth: MediaHealthState
  publisherState: PublisherState
  connectionFreshness: ConnectionFreshness
  dialogueSubstate: DialogueSubstate
  presenterId: string
  presenterName: string
  fallbackModeLabel?: string
  activeSkuId: string
  activeSkuCode: string
  activeSkuName: string
  activeSkuPriceVnd: number
  nextSkuName?: string
  pendingSwitch: PendingSkuSwitch | null
  sessionSkus: Array<{
    skuId: string
    skuCode: string
    name: string
    priceVnd: number
    eligible: boolean
    blockerReason?: string
  }>
  comments: LiveCommentItem[]
  currentTurn: SpeechTurnRecord | null
  completedTurnsCount: number
  storyCheckpointIndex: number
  storyTotalArcs: number
  commands: RuntimeCommandRecord[]
  canOperate: boolean
  canCopyInvite: boolean
  activeInviteUrl?: string
  isMockRuntime: true
}

/* ---------- M03-C: Invite Management & QR ---------- */

export interface ViewerInviteRecord {
  id: string
  sessionId: string
  sessionCode: string
  label: string
  token: string
  status: InviteStatus
  usageCap: number
  successfulAdmissions: number
  activeGuestCount: number
  expiresAt: string
  createdAt: string
  createdBy: string
  revokedAt?: string
}

export interface GuestAdmissionSession {
  guestSessionId: string
  inviteId: string
  sessionId: string
  nickname: string
  admittedAt: string
  active: boolean
  revoked: boolean
}

/* ---------- M03-D: Viewer Live Room ---------- */

export type ViewerRoomAccessState =
  | 'VALID'
  | 'EXPIRED'
  | 'REVOKED'
  | 'EXHAUSTED'
  | 'INVALID'

export interface ViewerRoomSnapshot {
  accessState: ViewerRoomAccessState
  accessReason?: string
  inviteId?: string
  inviteLabel?: string
  sessionId: string
  sessionTitle: string
  merchantName: string
  lifecycle: SessionLifecycle
  mediaHealth: MediaHealthState
  presenterId: string
  presenterName: string
  activeSku: {
    skuId: string
    skuCode: string
    name: string
    priceVnd: number
    packSpec: string
    ocopVerified: boolean
    ocopStars?: number
  } | null
  comments: Array<{
    id: string
    nickname: string
    body: string
    receivedAt: string
  }>
  guestSession: GuestAdmissionSession | null
  revision: number
}

/* ---------- M03-E: Session Reports ---------- */

export interface ReportMetricValue {
  key: string
  label: string
  value: number | string | null
  unit: string
  status: 'MEASURED' | 'PARTIAL' | 'NOT_AVAILABLE'
  source: string
  reason?: string
}

export interface ReportIntervalPoint {
  bucketLabel: string
  admissions: number
  concurrentViewers: number | null
}

export interface ReportTimelineSegment {
  id: string
  timeLabel: string
  title: string
  kind: 'LIVE' | 'AI_PAUSED' | 'MEDIA_DEGRADED' | 'STOPPED' | 'EMERGENCY'
  detail: string
}

export interface SessionReportDetail {
  sessionId: string
  sessionCode: string
  sessionTitle: string
  lifecycle: SessionLifecycle
  reportStatus: ReportStatus
  generatedAt: string
  isReducedOperatorView: boolean
  canExport: boolean
  kpis: ReportMetricValue[]
  intervalChart: ReportIntervalPoint[]
  hasConcurrentTelemetry: boolean
  timeline: ReportTimelineSegment[]
  aiFunnel: {
    commentsReceived: number
    commentsEligible: number
    turnsPrepared: number
    turnsCommitted: number
    turnsPlayedAck: number
    dedupedAckCount: number
  }
  mediaIncidents: Array<{
    id: string
    timeLabel: string
    severity: 'warning' | 'danger'
    summary: string
    fallbackUsed: string
  }>
  auditEvents: AccessAuditEvent[]
}
