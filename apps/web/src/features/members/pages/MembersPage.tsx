import { useState } from 'react'
import { Lock, MailPlus, ShieldCheck, Users } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Banner } from '@/components/ui/Banner'
import { Modal } from '@/components/ui/Modal'
import { Drawer } from '@/components/ui/Drawer'
import { Tabs } from '@/components/ui/Tabs'
import { EmptyState } from '@/components/ui/EmptyState'
import { Skeleton } from '@/components/ui/Skeleton'
import { useAuth } from '@/features/auth/hooks/useAuth'
import {
  useInviteOperator,
  useMembers,
  useUpdateAssignments,
} from '@/features/members/hooks/useMembers'
import { useSessions } from '@/features/live-session/hooks/useSessions'
import type { WorkspaceMember } from '@/types/m03'
import { formatShortTime } from '@/lib/format'

type TabKey = 'directory' | 'invitations' | 'audit'

export function MembersPage() {
  const { data: auth } = useAuth()
  const { data, isLoading } = useMembers()
  const { data: sessionsRes } = useSessions()
  const inviteMutation = useInviteOperator()
  const assignMutation = useUpdateAssignments()

  const [tab, setTab] = useState<TabKey>('directory')
  const [inviteOpen, setInviteOpen] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [selectedMember, setSelectedMember] = useState<WorkspaceMember | null>(null)
  const [draftSessionIds, setDraftSessionIds] = useState<string[]>([])
  const [notice, setNotice] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const isOwner = Boolean(auth?.capabilities.canManageMembers)

  if (auth && !isOwner) {
    return (
      <EmptyState
        tone="warning"
        icon={<Lock className="h-6 w-6" />}
        title="Chỉ Chủ sở hữu mới có quyền quản lý Thành viên & Phân quyền"
        description="Vận hành viên không thể mời thành viên hoặc thay đổi phân công phiên livestream."
      />
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  const members = data?.members ?? []
  const invitations = data?.invitations ?? []
  const auditLog = data?.auditLog ?? []
  const sessions = sessionsRes?.items ?? []

  const openMemberDrawer = (member: WorkspaceMember) => {
    setSelectedMember(member)
    setDraftSessionIds(member.assignedSessionIds)
    setErrorMsg(null)
  }

  const toggleSession = (sessionId: string) => {
    setDraftSessionIds((prev) =>
      prev.includes(sessionId)
        ? prev.filter((id) => id !== sessionId)
        : [...prev, sessionId],
    )
  }

  const handleSaveAssignments = async () => {
    if (!selectedMember) return
    setErrorMsg(null)
    try {
      const updated = await assignMutation.mutateAsync({
        memberId: selectedMember.id,
        assignedSessionIds: draftSessionIds,
        expectedRevision: selectedMember.revision,
      })
      setSelectedMember(updated)
      setNotice(
        `Đã lưu phân công phiên cho ${updated.displayName} (v${updated.revision}) và ghi Nhật ký truy cập.`,
      )
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Không thể lưu phân công.')
    }
  }

  const handleInviteSubmit = async () => {
    setErrorMsg(null)
    try {
      await inviteMutation.mutateAsync(inviteEmail)
      setInviteEmail('')
      setInviteOpen(false)
      setNotice('Đã tạo lời mời email cá nhân cho Vận hành viên (mô phỏng — không gửi email thật).')
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Không thể gửi lời mời.')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            Thành viên & Phân quyền
          </h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Phân công nhiều Vận hành viên cho cùng một phiên (N:N). Quyền Chủ thể hình ảnh (Rights Subject) được quản lý độc lập.
          </p>
        </div>

        <Button
          variant="primary"
          leftIcon={<MailPlus className="h-4 w-4" />}
          onClick={() => setInviteOpen(true)}
        >
          Mời Vận hành viên
        </Button>
      </div>

      {notice ? <Banner severity="info" title="Cập nhật phân quyền" description={notice} /> : null}
      {errorMsg ? <Banner severity="danger" title="Không thể thực hiện" description={errorMsg} /> : null}

      <Tabs<TabKey>
        activeId={tab}
        onChange={setTab}
        items={[
          { id: 'directory', label: 'Danh bạ thành viên', count: members.length },
          { id: 'invitations', label: 'Lời mời Operator', count: invitations.length },
          { id: 'audit', label: 'Nhật ký truy cập', count: auditLog.length },
        ]}
      />

      {tab === 'directory' ? (
        <>
          <Card padding="none" className="hidden xl:block overflow-hidden">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--border-default)] bg-[var(--bg-subtle)] text-xs font-semibold text-[var(--text-secondary)]">
                  <th className="px-5 py-3">Thành viên</th>
                  <th className="px-4 py-3">Vai trò</th>
                  <th className="px-4 py-3">Trạng thái</th>
                  <th className="px-4 py-3">Phiên được phân công</th>
                  <th className="px-5 py-3 text-right">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-default)]">
                {members.map((m) => (
                  <tr key={m.id} className="hover:bg-[var(--bg-subtle)]/60">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--brand-navy)] text-xs font-bold text-white">
                          {m.initials}
                        </div>
                        <div>
                          <p className="font-semibold text-[var(--text-primary)]">{m.displayName}</p>
                          <p className="text-xs text-[var(--text-muted)]">{m.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      <StatusBadge
                        label={m.roleLabel}
                        tone={m.role === 'OWNER' ? 'info' : 'neutral'}
                      />
                    </td>
                    <td className="px-4 py-3.5">
                      <StatusBadge label="Đang hoạt động" tone="success" />
                    </td>
                    <td className="px-4 py-3.5 text-xs text-[var(--text-secondary)]">
                      {m.role === 'OWNER'
                        ? 'Toàn bộ phiên workspace'
                        : m.assignedSessionIds.length > 0
                          ? m.assignedSessionIds.map((sid) => sid.replace('ses-', 'Phiên #')).join(', ')
                          : 'Chưa phân công phiên nào'}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      {m.role === 'OPERATOR' ? (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => openMemberDrawer(m)}
                        >
                          Phân công phiên
                        </Button>
                      ) : (
                        <span className="text-xs text-[var(--text-muted)]">Chủ sở hữu</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:hidden">
            {members.map((m) => (
              <Card key={m.id} padding="sm" className="space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--brand-navy)] text-xs font-bold text-white">
                      {m.initials}
                    </div>
                    <div>
                      <p className="text-sm font-bold">{m.displayName}</p>
                      <p className="text-xs text-[var(--text-muted)]">{m.email}</p>
                    </div>
                  </div>
                  <StatusBadge label={m.roleLabel} tone={m.role === 'OWNER' ? 'info' : 'neutral'} />
                </div>
                <p className="text-xs text-[var(--text-secondary)]">
                  Phân công:{' '}
                  {m.role === 'OWNER'
                    ? 'Toàn bộ workspace'
                    : m.assignedSessionIds.length > 0
                      ? m.assignedSessionIds.join(', ')
                      : 'Chưa có phiên'}
                </p>
                {m.role === 'OPERATOR' ? (
                  <Button
                    variant="secondary"
                    size="sm"
                    className="w-full"
                    onClick={() => openMemberDrawer(m)}
                  >
                    Quản lý phân công phiên
                  </Button>
                ) : null}
              </Card>
            ))}
          </div>
        </>
      ) : null}

      {tab === 'invitations' ? (
        <Card padding="md">
          <ul className="divide-y divide-[var(--border-default)]">
            {invitations.map((inv) => (
              <li key={inv.id} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
                <div>
                  <p className="font-semibold text-[var(--text-primary)]">{inv.email}</p>
                  <p className="text-xs text-[var(--text-muted)]">
                    Mời bởi {inv.invitedBy} · Hết hạn: {formatShortTime(inv.expiresAt)}
                  </p>
                </div>
                <StatusBadge
                  label={
                    inv.status === 'PENDING'
                      ? 'Đang chờ chấp nhận'
                      : inv.status === 'EXPIRED'
                        ? 'Đã hết hạn'
                        : 'Đã thu hồi'
                  }
                  tone={inv.status === 'PENDING' ? 'warning' : 'neutral'}
                />
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {tab === 'audit' ? (
        <Card padding="md">
          <ul className="divide-y divide-[var(--border-default)] text-xs">
            {auditLog.map((ev) => (
              <li key={ev.id} className="py-3 flex flex-wrap items-start justify-between gap-2">
                <div className="space-y-0.5">
                  <p className="font-semibold text-[var(--text-primary)]">
                    {ev.actorName} · {ev.action} · {ev.targetLabel}
                  </p>
                  <p className="text-[var(--text-secondary)]">{ev.reason}</p>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge
                    label={ev.decision === 'APPLIED' ? 'Đã áp dụng' : 'Từ chối'}
                    tone={ev.decision === 'APPLIED' ? 'success' : 'danger'}
                  />
                  <span className="text-[var(--text-muted)] tabular-nums">
                    {formatShortTime(ev.occurredAt)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <Card padding="sm" className="flex items-center gap-2.5 bg-[var(--bg-subtle)] text-xs text-[var(--text-secondary)]">
        <ShieldCheck className="h-4 w-4 shrink-0" />
        <span>
          Lưu ý: Lời mời Vận hành viên qua email khác hoàn toàn Lời mời xem livestream của khách và Cổng xác nhận quyền của Chủ thể hình ảnh (Rights Subject).
        </span>
      </Card>

      {/* Member Detail & Session Assignment Drawer (MP-D3=A) */}
      <Drawer
        open={Boolean(selectedMember)}
        onClose={() => setSelectedMember(null)}
        title={selectedMember?.displayName ?? 'Chi tiết thành viên'}
        subtitle={
          selectedMember
            ? `${selectedMember.email} · Revision v${selectedMember.revision}`
            : undefined
        }
      >
        {selectedMember ? (
          <div className="space-y-5">
            <div className="rounded-[10px] bg-[var(--bg-subtle)] p-3.5 text-xs text-[var(--text-secondary)] space-y-1">
              <p className="font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
                <Users className="h-4 w-4" /> Phân công phiên livestream (N:N)
              </p>
              <p>
                Một phiên có thể có nhiều Vận hành viên đồng thời. Gỡ quyền của thành viên này không ảnh hưởng Vận hành viên khác và không tự dừng luồng đang phát.
              </p>
            </div>

            <div className="space-y-2.5">
              {sessions.map((s) => {
                const checked = draftSessionIds.includes(s.id)
                return (
                  <label
                    key={s.id}
                    className="flex items-center justify-between gap-3 rounded-[10px] border border-[var(--border-default)] p-3 cursor-pointer hover:bg-[var(--bg-subtle)]"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleSession(s.id)}
                        className="h-4 w-4 accent-[var(--brand-amber)]"
                      />
                      <div className="min-w-0">
                        <p className="text-sm font-semibold truncate">
                          {s.code} · {s.title}
                        </p>
                        <p className="text-xs text-[var(--text-muted)]">
                          Trạng thái: {s.lifecycle}
                        </p>
                      </div>
                    </div>
                  </label>
                )
              })}
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-[var(--border-default)]">
              <Button variant="secondary" onClick={() => setSelectedMember(null)}>
                Đóng
              </Button>
              <Button
                variant="primary"
                loading={assignMutation.isPending}
                onClick={handleSaveAssignments}
              >
                Lưu phân công
              </Button>
            </div>
          </div>
        ) : null}
      </Drawer>

      {/* Invite Operator Modal */}
      <Modal
        open={inviteOpen}
        onClose={() => setInviteOpen(false)}
        title="Mời Vận hành viên mới qua email"
        description="Lời mời có hiệu lực 7 ngày, gắn đúng danh tính email người nhận (mô phỏng)."
        footer={
          <>
            <Button variant="secondary" onClick={() => setInviteOpen(false)}>
              Hủy
            </Button>
            <Button
              variant="primary"
              loading={inviteMutation.isPending}
              onClick={handleInviteSubmit}
            >
              Gửi lời mời
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <label htmlFor="op-email" className="block text-xs font-semibold">
            Email người nhận *
          </label>
          <input
            id="op-email"
            type="email"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            placeholder="ten.operator@muonglat.vn"
            className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm"
          />
        </div>
      </Modal>
    </div>
  )
}
