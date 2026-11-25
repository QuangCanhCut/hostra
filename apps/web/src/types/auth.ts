export type UserRole = 'OWNER' | 'OPERATOR'

export interface WorkspaceSummary {
  id: string
  displayName: string
  merchantLegalName: string
  ownerId: string
  onboardingCompleted: boolean
  onboardingStep: number
  onboardingTotalSteps: number
  revision: number
}

export interface ActorProfile {
  id: string
  displayName: string
  email: string
  initials: string
  role: UserRole
  roleLabel: string
  assignedSessionIds: string[]
}

export interface UserCapabilities {
  canCreateSession: boolean
  canStartSession: boolean
  canOperateAssignedSession: boolean
  canApproveContent: boolean
  canSubmitOcop: boolean
  canManageMembers: boolean
  canManageInvites: boolean
  canExportReports: boolean
  canManagePresenters: boolean
}

export interface AuthSnapshot {
  authenticated: boolean
  actor: ActorProfile
  workspace: WorkspaceSummary
  capabilities: UserCapabilities
  verifiedAt: string
}
