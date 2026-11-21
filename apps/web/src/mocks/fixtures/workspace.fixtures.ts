import type {
  ActorProfile,
  AuthSnapshot,
  UserCapabilities,
  UserRole,
  WorkspaceSummary,
} from '@/types/auth'

export const WORKSPACE_PRIMARY: WorkspaceSummary = {
  id: 'ws-muong-lat-01',
  displayName: 'Đặc sản Mường Lát',
  merchantLegalName: 'HTX Nông sản & Đặc sản Mường Lát',
  ownerId: 'usr-owner-01',
  onboardingCompleted: true,
  onboardingStep: 4,
  onboardingTotalSteps: 4,
  revision: 18,
}

export const WORKSPACE_NEW_EMPTY: WorkspaceSummary = {
  ...WORKSPACE_PRIMARY,
  onboardingCompleted: false,
  onboardingStep: 1,
  revision: 1,
}

export const OWNER_ACTOR: ActorProfile = {
  id: 'usr-owner-01',
  displayName: 'Nguyễn Minh Quân',
  email: 'quan.nguyen@muonglat.vn',
  initials: 'MQ',
  role: 'OWNER',
  roleLabel: 'Chủ sở hữu',
  assignedSessionIds: ['ses-014', 'ses-015', 'ses-013', 'ses-012'],
}

export const OPERATOR_LAN: ActorProfile = {
  id: 'usr-op-01',
  displayName: 'Trần Ngọc Lan',
  email: 'lan.tran@muonglat.vn',
  initials: 'NL',
  role: 'OPERATOR',
  roleLabel: 'Vận hành viên',
  assignedSessionIds: ['ses-014', 'ses-013'],
}

export const OPERATOR_BINH: ActorProfile = {
  id: 'usr-op-02',
  displayName: 'Lê Thanh Bình',
  email: 'binh.le@muonglat.vn',
  initials: 'TB',
  role: 'OPERATOR',
  roleLabel: 'Vận hành viên',
  assignedSessionIds: ['ses-014'],
}

export const WORKSPACE_MEMBERS: ActorProfile[] = [
  OWNER_ACTOR,
  OPERATOR_LAN,
  OPERATOR_BINH,
]

export const OWNER_CAPABILITIES: UserCapabilities = {
  canCreateSession: true,
  canStartSession: true,
  canOperateAssignedSession: true,
  canApproveContent: true,
  canSubmitOcop: true,
  canManageMembers: true,
  canManageInvites: true,
  canExportReports: true,
  canManagePresenters: true,
}

export const OPERATOR_CAPABILITIES: UserCapabilities = {
  canCreateSession: false,
  canStartSession: false,
  canOperateAssignedSession: true,
  canApproveContent: false,
  canSubmitOcop: false,
  canManageMembers: false,
  canManageInvites: false,
  canExportReports: false,
  canManagePresenters: false,
}

export function buildAuthSnapshot(
  role: UserRole,
  options?: { emptyWorkspace?: boolean; unassignedOperator?: boolean },
): AuthSnapshot {
  const isOwner = role === 'OWNER'
  const actor = isOwner
    ? OWNER_ACTOR
    : options?.unassignedOperator
      ? { ...OPERATOR_LAN, assignedSessionIds: [] }
      : OPERATOR_LAN

  return {
    authenticated: true,
    actor,
    workspace: options?.emptyWorkspace ? WORKSPACE_NEW_EMPTY : WORKSPACE_PRIMARY,
    capabilities: isOwner ? OWNER_CAPABILITIES : OPERATOR_CAPABILITIES,
    verifiedAt: '2026-11-21T08:15:00Z',
  }
}
