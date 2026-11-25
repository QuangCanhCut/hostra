import { apiRequest, type RequestContext } from '@/services/api-client'
import type {
  AccessAuditEvent,
  OperatorInvitation,
  WorkspaceMember,
} from '@/types/m03'

export interface MembersResponse {
  members: WorkspaceMember[]
  invitations: OperatorInvitation[]
  auditLog: AccessAuditEvent[]
}

export function fetchMembers(context: RequestContext): Promise<MembersResponse> {
  return apiRequest<MembersResponse>('/api/mock/v1/members', context)
}

export function inviteOperator(
  email: string,
  context: RequestContext,
): Promise<OperatorInvitation> {
  return apiRequest<OperatorInvitation>('/api/mock/v1/members/invite', context, {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

export function updateMemberAssignments(
  memberId: string,
  assignedSessionIds: string[],
  expectedRevision: number,
  context: RequestContext,
): Promise<WorkspaceMember> {
  return apiRequest<WorkspaceMember>(
    `/api/mock/v1/members/${memberId}/assignments`,
    context,
    {
      method: 'PUT',
      body: JSON.stringify({ assignedSessionIds, expectedRevision }),
    },
  )
}
