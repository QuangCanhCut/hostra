import type {
  KnowledgeApprovalStatus,
  OcopVerificationStatus,
  PresenterStylePreset,
  PresenterSummary,
  ProductSkuSummary,
  RightsConsentStatus,
  SessionSummary,
} from '@/types/domain'

/* ---------- M02-A: Presenter Studio ---------- */

export interface PresenterClip {
  id: string
  label: string
  role: 'INTRO' | 'EXPLAIN' | 'IDLE'
  durationSec: number
  qcStatus: 'PENDING' | 'PASS' | 'FAIL'
  qcNote?: string
}

export interface PresenterPackCandidate {
  packId: string
  versionLabel: string
  stylePreset: PresenterStylePreset
  styleLabel: string
  motionTemplate: string
  generatedAt: string
  qcStatus: 'PENDING' | 'PASS' | 'FAIL_PARTIAL' | 'FAIL'
  rightsVersion: number
  clips: PresenterClip[]
}

export interface RightsConsentRecord {
  requestId: string
  presenterId: string
  subjectName: string
  purpose: string
  imageVideoScope: boolean
  voiceCloneScope: boolean
  status: RightsConsentStatus
  rightsVersion: number
  expiresAt: string
  updatedAt: string
}

export interface PresenterDetail extends PresenterSummary {
  subjectName: string
  portraitNote: string
  rightsConsent: RightsConsentRecord
  candidates: PresenterPackCandidate[]
  selectedCandidateId: string | null
  approvedPackId: string | null
  jobStageLabel: string
  jobErrorMessage?: string
  linkedSessionCodes: string[]
}

export interface PresenterDraftPayload {
  displayName: string
  subjectName: string
  portraitFileName: string
  stylePreset: PresenterStylePreset
  voicePresetLabel: string
  step: number
}

/* ---------- M02-B: Products & OCOP ---------- */

export interface EvidenceFile {
  id: string
  fileName: string
  documentType: 'OCOP_CERT' | 'FOOD_SAFETY' | 'PRODUCT_LABEL' | 'ORIGIN_DOC'
  documentTypeLabel: string
  uploadedBy: string
  uploadedAt: string
  sizeKb: number
  provenanceNote: string
}

export interface MissingEvidenceItem {
  id: string
  label: string
  required: boolean
  satisfied: boolean
}

export interface ProductVersionEntry {
  version: number
  updatedAt: string
  actorName: string
  summary: string
}

export interface ProductDetail extends ProductSkuSummary {
  description: string
  brandName: string
  expiryLabel: string
  ocopAuthoritySource?: string
  ocopDecisionCode?: string
  ocopReasonNote: string
  ocopCheckedAt?: string
  submittedByOwner: boolean
  evidenceFiles: EvidenceFile[]
  missingChecklist: MissingEvidenceItem[]
  versions: ProductVersionEntry[]
  linkedSessionCodes: string[]
  revision: number
}

export interface ProductDraftPayload {
  name: string
  skuCode: string
  category: string
  priceVnd: number
  packSpec: string
  origin: string
  expiryLabel: string
  description: string
  ocopDecisionCode: string
  step: number
}

/* ---------- M02-C: Knowledge & Claims ---------- */

export type FactGroupKey =
  | 'PRICE'
  | 'SPECS'
  | 'ORIGIN'
  | 'POLICY'
  | 'MARKETING_CLAIMS'

export type FactDecisionStatus =
  | 'REVIEW_REQUIRED'
  | 'APPROVED'
  | 'NEEDS_EVIDENCE'
  | 'BLOCKED'
  | 'REJECTED'

export interface KnowledgeFactItem {
  id: string
  group: FactGroupKey
  label: string
  proposedValue: string
  sourceFile: string
  sourcePage: string
  sourceExcerpt: string
  decision: FactDecisionStatus
  policyRiskNote?: string
  reviewerNote?: string
  required: boolean
}

export interface KnowledgeVersionEntry {
  version: number
  status: KnowledgeApprovalStatus
  approvedBy?: string
  approvedAt?: string
  summary: string
  beforeValue?: string
  afterValue?: string
}

export interface KnowledgePackageDetail {
  skuId: string
  skuCode: string
  productName: string
  ocopStatus: OcopVerificationStatus
  approvalStatus: KnowledgeApprovalStatus
  extractionStatus: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED'
  activeVersion: number
  draftRevision: number
  sourceDocTitle: string
  sourceDocVersion: string
  sourceDocPassages: Array<{ page: string; heading: string; text: string }>
  items: KnowledgeFactItem[]
  speechPreviewLines: Array<{ text: string; sourceRef: string }>
  versions: KnowledgeVersionEntry[]
  updatedAt: string
}

/* ---------- M02-D: Story Planner ---------- */

export interface StoryArcItem {
  id: string
  position: number
  title: string
  durationMin: number
  skuId: string | null
  skuLabel: string
  topic: string
  previewText: string
  factRefs: string[]
  reviewed: boolean
}

export interface StoryAiProposal {
  proposalId: string
  prompt: string
  summary: string
  unsupportedWarning?: string
  beforeSummary: string
  afterSummary: string
  proposedArcs: StoryArcItem[]
  status: 'PROPOSAL_READY' | 'APPLIED' | 'REJECTED'
}

export interface StoryPlanDetail {
  sessionId: string
  sessionCode: string
  sessionTitle: string
  planRevision: number
  approvedRevision: number | null
  approvalStatus: 'DRAFT' | 'REVIEW_REQUIRED' | 'APPROVED' | 'INVALIDATED'
  dirtyReason?: string
  approvedBy?: string
  approvedAt?: string
  arcs: StoryArcItem[]
  lastProposal: StoryAiProposal | null
  revisionHistory: Array<{
    revision: number
    actor: string
    summary: string
    timestamp: string
  }>
}

/* ---------- M02-E & F: Live Session Setup & Readiness ---------- */

export interface SessionDetail extends SessionSummary {
  goal: string
  theme: string
  estimatedMinutes: number
  prioritySkuId: string | null
  mandatoryMessages: string
  selectedSkuIds: string[]
  selectedPresenterVersion: string
  storyApprovalStatus: 'DRAFT' | 'REVIEW_REQUIRED' | 'APPROVED' | 'INVALIDATED'
  readinessOverall: 'READY' | 'BLOCKED' | 'CHECKING'
  readinessBlockedCount: number
}

export type ReadinessGateStatus = 'PASS' | 'PENDING' | 'BLOCKED'

export interface ReadinessGateItem {
  id: string
  label: string
  status: ReadinessGateStatus
  reason: string
  sourceLabel: string
  remediationLabel?: string
  remediationRoute?: string
}

export interface ReadinessSnapshot {
  sessionId: string
  sessionCode: string
  sessionTitle: string
  sessionLifecycle: SessionSummary['lifecycle']
  overallReady: boolean
  blockedCount: number
  pendingCount: number
  checkedAt: string
  revision: number
  gates: ReadinessGateItem[]
}

export interface StartCommandResult {
  commandId: string
  status: 'REQUESTED' | 'ACCEPTED' | 'APPLIED' | 'REJECTED'
  lifecycle: SessionSummary['lifecycle']
  reason: string
  isMockRuntime: true
}

/* ---------- Workspace Onboarding ---------- */

export interface OnboardingDraft {
  workspaceName: string
  merchantLegalName: string
  categoryFocus: string
  step: number
  savedAt: string
  revision: number
}
