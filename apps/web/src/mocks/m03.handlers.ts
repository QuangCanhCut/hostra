import { delay, http, HttpResponse } from 'msw'
import type { UserRole } from '@/types/auth'
import type { MockScenarioKey } from '@/types/scenario'
import type { RuntimeCommandType } from '@/types/m03'
import { getStore } from '@/mocks/store'
import {
  advanceSpeechTurnPhase,
  buildControlRoomSnapshot,
  buildSessionReport,
  buildViewerRoomSnapshot,
  getM03Store,
  getOrCreateRuntime,
  isActorAssignedToSession,
} from '@/mocks/m03.store'

function readScenario(request: Request): MockScenarioKey {
  return (request.headers.get('X-Hostra-Scenario') as MockScenarioKey) || 'happy-path'
}

function readRole(request: Request): UserRole {
  const value = request.headers.get('X-Hostra-Role')?.toUpperCase()
  return value === 'OPERATOR' ? 'OPERATOR' : 'OWNER'
}

function actorNameForRole(role: UserRole): string {
  return role === 'OWNER' ? 'Nguyễn Minh Quân' : 'Trần Ngọc Lan'
}

function forbidden(message: string) {
  return HttpResponse.json({ code: 'FORBIDDEN', message }, { status: 403 })
}

export const m03Handlers = [
  /* ---------- M03-B: Members & Permissions ---------- */
  http.get('/api/mock/v1/members', async ({ request }) => {
    const role = readRole(request)
    if (role !== 'OWNER') {
      return forbidden('Chỉ Chủ sở hữu mới có quyền quản lý danh bạ thành viên.')
    }
    await delay(50)
    const m03 = getM03Store(readScenario(request))
    return HttpResponse.json({
      members: m03.members,
      invitations: m03.operatorInvites,
      auditLog: m03.auditLog,
    })
  }),

  http.post('/api/mock/v1/members/invite', async ({ request }) => {
    const role = readRole(request)
    if (role !== 'OWNER') {
      return forbidden('Chỉ Chủ sở hữu mới có quyền mời Vận hành viên.')
    }
    const m03 = getM03Store(readScenario(request))
    const body = (await request.json()) as { email: string; expiresInDays?: number }
    const email = body.email.trim().toLowerCase()
    if (!email || !email.includes('@')) {
      return HttpResponse.json({ message: 'Vui lòng nhập email hợp lệ.' }, { status: 400 })
    }
    const duplicate = m03.operatorInvites.some(
      (i) => i.email.toLowerCase() === email && i.status === 'PENDING',
    )
    if (duplicate) {
      return HttpResponse.json(
        { message: 'Email này đã có lời mời đang chờ chấp nhận.' },
        { status: 409 },
      )
    }
    const created = {
      id: `op-inv-${Date.now()}`,
      email,
      status: 'PENDING' as const,
      expiresAt: '2026-11-28T23:59:00Z',
      invitedBy: 'Nguyễn Minh Quân',
      createdAt: new Date().toISOString(),
    }
    m03.operatorInvites.unshift(created)
    m03.auditLog.unshift({
      id: `aud-${Date.now()}`,
      occurredAt: new Date().toISOString(),
      actorName: 'Nguyễn Minh Quân',
      action: 'INVITE_OPERATOR',
      targetLabel: email,
      decision: 'APPLIED',
      reason: 'Gửi lời mời email cá nhân có thời hạn (mô phỏng)',
    })
    return HttpResponse.json(created, { status: 201 })
  }),

  http.put('/api/mock/v1/members/:memberId/assignments', async ({ request, params }) => {
    const role = readRole(request)
    if (role !== 'OWNER') {
      return forbidden('Chỉ Chủ sở hữu mới được phân công phiên cho Vận hành viên.')
    }
    const scenario = readScenario(request)
    const m03 = getM03Store(scenario)
    const core = getStore(scenario)
    const member = m03.members.find((m) => m.id === params.memberId)
    if (!member) {
      return HttpResponse.json({ message: 'Không tìm thấy thành viên.' }, { status: 404 })
    }
    const body = (await request.json()) as {
      assignedSessionIds: string[]
      expectedRevision: number
    }
    if (body.expectedRevision !== member.revision) {
      return HttpResponse.json(
        { message: 'Xung đột phiên bản phân quyền (409). Vui lòng tải lại trước khi lưu.' },
        { status: 409 },
      )
    }
    member.assignedSessionIds = Array.from(new Set(body.assignedSessionIds))
    member.revision += 1

    // Synchronize canonical session assignedOperatorIds
    for (const s of core.sessions) {
      const hasMember = member.assignedSessionIds.includes(s.id)
      const exists = s.assignedOperatorIds.includes(member.id)
      if (hasMember && !exists) s.assignedOperatorIds.push(member.id)
      if (!hasMember && exists) {
        s.assignedOperatorIds = s.assignedOperatorIds.filter((id) => id !== member.id)
      }
    }

    m03.auditLog.unshift({
      id: `aud-${Date.now()}`,
      occurredAt: new Date().toISOString(),
      actorName: 'Nguyễn Minh Quân',
      action: 'UPDATE_ASSIGNMENTS',
      targetLabel: `${member.displayName} → ${member.assignedSessionIds.join(', ') || 'Không có phiên'}`,
      decision: 'APPLIED',
      reason: 'Cập nhật phân công phiên N:N (không ảnh hưởng Vận hành viên khác)',
    })
    return HttpResponse.json(member)
  }),

  /* ---------- M03-A: Live Control Room ---------- */
  http.get('/api/mock/v1/sessions/:id/control', async ({ request, params }) => {
    await delay(60)
    const scenario = readScenario(request)
    const role = readRole(request)
    const sessionId = String(params.id)
    if (!isActorAssignedToSession(scenario, role, sessionId)) {
      return forbidden('Bạn không được phân công vào phiên livestream này hoặc quyền đã bị thu hồi.')
    }
    const snap = buildControlRoomSnapshot(scenario, role, sessionId)
    if (!snap) return HttpResponse.json({ message: 'Không tìm thấy phiên.' }, { status: 404 })
    return HttpResponse.json(snap)
  }),

  http.post('/api/mock/v1/sessions/:id/control/command', async ({ request, params }) => {
    await delay(120)
    const scenario = readScenario(request)
    const role = readRole(request)
    const sessionId = String(params.id)

    if (!isActorAssignedToSession(scenario, role, sessionId)) {
      return forbidden('Quyền vận hành phiên này đã bị thu hồi hoặc chưa được cấp.')
    }

    const core = getStore(scenario)
    const m03 = getM03Store(scenario)
    const session = core.sessions.find((s) => s.id === sessionId)
    if (!session) return HttpResponse.json({ message: 'Không tìm thấy phiên.' }, { status: 404 })
    const rt = getOrCreateRuntime(scenario, sessionId)

    const body = (await request.json()) as {
      type: RuntimeCommandType
      expectedRevision: number
      targetSkuId?: string
      commentId?: string
      simulatePhase?: 'ACCEPT_ONLY' | 'APPLY'
    }

    const actorName = actorNameForRole(role)
    const cmdId = `cmd-${Date.now()}`

    // Revision conflict simulation (except EMERGENCY_STOP which overrides normal revision)
    if (body.type !== 'EMERGENCY_STOP' && body.expectedRevision !== session.revision) {
      const rejected = {
        commandId: cmdId,
        type: body.type,
        actorId: role === 'OWNER' ? 'usr-owner-01' : 'usr-op-01',
        actorName,
        expectedRevision: body.expectedRevision,
        sessionEpoch: session.epoch,
        status: 'REJECTED' as const,
        reason: `Xung đột revision (409): yêu cầu v${body.expectedRevision}, hiện tại v${session.revision}`,
        requestedAt: new Date().toISOString(),
      }
      rt.commands.unshift(rejected)
      return HttpResponse.json({ command: rejected, snapshot: buildControlRoomSnapshot(scenario, role, sessionId) }, { status: 409 })
    }

    let status: 'ACCEPTED' | 'APPLIED' | 'REJECTED' = 'APPLIED'
    let reason = 'Đã áp dụng thành công'

    switch (body.type) {
      case 'PAUSE_AI':
        session.aiState = 'PAUSED'
        rt.dialogueSubstate = 'IDLE'
        reason = 'AI đã tạm dừng. Luồng livestream vẫn đang LIVE với cảnh an toàn.'
        break
      case 'RESUME_AI':
        session.aiState = 'ACTIVE'
        rt.dialogueSubstate = 'PLAYING_SCRIPT'
        reason = 'AI đã tiếp tục hoạt động sau kiểm tra điều kiện.'
        break
      case 'SWITCH_SKU': {
        const target = core.products.find((p) => p.skuId === body.targetSkuId)
        if (!target || target.ocopStatus !== 'VERIFIED' || target.knowledgeStatus !== 'APPROVED') {
          status = 'REJECTED'
          reason = 'SKU đích chưa đạt đủ điều kiện OCOP/Tri thức để chuyển.'
          break
        }
        if (body.simulatePhase === 'ACCEPT_ONLY') {
          status = 'ACCEPTED'
          rt.pendingSwitch = {
            commandId: cmdId,
            targetSkuId: target.skuId,
            targetSkuCode: target.skuCode,
            targetSkuName: target.name,
            actorName,
            status: 'ACCEPTED',
            requestedAt: new Date().toISOString(),
          }
          reason = `Đã tiếp nhận lệnh chuyển sang ${target.skuCode} (chờ safe boundary — Active SKU chưa đổi).`
        } else {
          rt.activeSkuId = target.skuId
          session.activeSkuName = target.name
          rt.pendingSwitch = null
          reason = `Đã áp dụng chuyển Active SKU sang ${target.skuCode} · ${target.name}.`
        }
        break
      }
      case 'PRIORITIZE_COMMENT': {
        const c = rt.comments.find((x) => x.id === body.commentId)
        if (!c || c.queueStatus === 'COMMITTED' || c.queueStatus === 'PLAYED') {
          status = 'REJECTED'
          reason = 'Bình luận đã được chốt phát hoặc không còn trong hàng đợi.'
        } else {
          c.queueStatus = 'PRIORITIZED'
          c.priorityScore = 99
          reason = `Đã ưu tiên bình luận của ${c.nickname} trong hàng đợi.`
        }
        break
      }
      case 'SKIP_PENDING': {
        const c = rt.comments.find((x) => x.id === body.commentId)
        if (!c || c.queueStatus === 'COMMITTED' || c.queueStatus === 'PLAYED') {
          status = 'REJECTED'
          reason = 'Không thể bỏ qua (Skip) câu đã COMMITTED hoặc đã phát.'
        } else {
          c.queueStatus = 'SKIPPED'
          reason = `Đã bỏ qua câu hỏi chờ của ${c.nickname} trước thời điểm commit.`
        }
        break
      }
      case 'STOP':
        if (body.simulatePhase === 'ACCEPT_ONLY') {
          status = 'ACCEPTED'
          session.lifecycle = 'STOPPING'
          reason = 'Đã gửi lệnh kết thúc phiên (STOPPING). Chờ xác nhận publisher.'
        } else {
          session.lifecycle = 'STOPPED'
          session.aiState = 'PAUSED'
          session.stoppedAt = new Date().toISOString()
          rt.publisherState = 'DISCONNECTED'
          reason = 'Phiên livestream đã kết thúc an toàn (STOPPED).'
        }
        break
      case 'EMERGENCY_STOP':
        session.lifecycle = 'STOPPED'
        session.aiState = 'BLOCKED'
        session.stoppedAt = new Date().toISOString()
        rt.publisherState = 'DISCONNECTED'
        reason = 'Dừng khẩn cấp đã thực thi ngay không chờ Chủ sở hữu online (ghi Audit).'
        break
    }

    if (status !== 'REJECTED') {
      session.revision += 1
    }

    const record = {
      commandId: cmdId,
      type: body.type,
      actorId: role === 'OWNER' ? 'usr-owner-01' : 'usr-op-01',
      actorName,
      expectedRevision: body.expectedRevision,
      sessionEpoch: session.epoch,
      status,
      reason,
      requestedAt: new Date().toISOString(),
    }
    rt.commands.unshift(record)
    m03.auditLog.unshift({
      id: `aud-${Date.now()}`,
      occurredAt: record.requestedAt,
      actorName,
      action: body.type,
      targetLabel: session.code,
      decision: status === 'REJECTED' ? 'REJECTED' : 'APPLIED',
      reason,
      sessionId,
    })

    return HttpResponse.json({
      command: record,
      snapshot: buildControlRoomSnapshot(scenario, role, sessionId),
    })
  }),

  http.post('/api/mock/v1/sessions/:id/control/advance-speech', async ({ request, params }) => {
    const scenario = readScenario(request)
    const role = readRole(request)
    const sessionId = String(params.id)
    advanceSpeechTurnPhase(scenario, sessionId)
    return HttpResponse.json(buildControlRoomSnapshot(scenario, role, sessionId))
  }),

  http.post('/api/mock/v1/sessions/:id/control/simulate-event', async ({ request, params }) => {
    const scenario = readScenario(request)
    const role = readRole(request)
    const sessionId = String(params.id)
    const core = getStore(scenario)
    const rt = getOrCreateRuntime(scenario, sessionId)
    const session = core.sessions.find((s) => s.id === sessionId)
    const body = (await request.json()) as {
      kind: 'TOGGLE_DEGRADED' | 'TOGGLE_STALE' | 'SIMULATE_CONFLICT'
    }

    if (body.kind === 'TOGGLE_DEGRADED' && session) {
      const nextDegraded = session.mediaHealth !== 'DEGRADED'
      session.mediaHealth = nextDegraded ? 'DEGRADED' : 'HEALTHY'
      rt.publisherState = nextDegraded ? 'DEGRADED' : 'CONNECTED'
      session.fallbackDescription = nextDegraded
        ? 'Đang dùng cảnh sản phẩm dự phòng + âm thanh xác minh'
        : undefined
      session.revision += 1
    } else if (body.kind === 'TOGGLE_STALE') {
      rt.connectionFreshness =
        rt.connectionFreshness === 'CONNECTED' ? 'STALE' : 'CONNECTED'
    } else if (body.kind === 'SIMULATE_CONFLICT' && session) {
      session.revision += 1
      rt.commands.unshift({
        commandId: `cmd-conflict-sim-${Date.now()}`,
        type: 'PAUSE_AI',
        actorId: 'usr-op-02',
        actorName: 'Lê Thanh Bình',
        expectedRevision: session.revision - 1,
        sessionEpoch: session.epoch,
        status: 'APPLIED',
        reason: 'Lê Thanh Bình vừa cập nhật trạng thái lên revision mới — lệnh cũ sẽ bị 409 conflict',
        requestedAt: new Date().toISOString(),
      })
    }

    return HttpResponse.json(buildControlRoomSnapshot(scenario, role, sessionId))
  }),

  /* ---------- M03-C: Invite Management ---------- */
  http.get('/api/mock/v1/invites', async ({ request }) => {
    const role = readRole(request)
    if (role !== 'OWNER') {
      return forbidden('Chỉ Chủ sở hữu mới có quyền quản lý lời mời xem livestream.')
    }
    await delay(50)
    const url = new URL(request.url)
    const sessionId = url.searchParams.get('sessionId')
    const m03 = getM03Store(readScenario(request))
    const items = sessionId
      ? m03.invites.filter((i) => i.sessionId === sessionId)
      : m03.invites
    return HttpResponse.json({ items })
  }),

  http.post('/api/mock/v1/invites', async ({ request }) => {
    const role = readRole(request)
    if (role !== 'OWNER') {
      return forbidden('Chỉ Chủ sở hữu mới có quyền tạo liên kết mời.')
    }
    await delay(100)
    const scenario = readScenario(request)
    const m03 = getM03Store(scenario)
    const core = getStore(scenario)
    const body = (await request.json()) as {
      sessionId: string
      label: string
      usageCap: number
      expiresAt: string
    }
    if (!body.label.trim() || body.usageCap < 1) {
      return HttpResponse.json(
        { message: 'Vui lòng nhập tên liên kết và giới hạn lượt tham gia > 0.' },
        { status: 400 },
      )
    }
    const session = core.sessions.find((s) => s.id === body.sessionId)
    const slug = body.label
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')
      .slice(0, 14)

    const created = {
      id: `inv-${Date.now()}`,
      sessionId: body.sessionId,
      sessionCode: session?.code ?? 'Phiên #014',
      label: body.label.trim(),
      token: `${slug || 'guest'}-${Math.floor(1000 + (m03.invites.length * 137) % 8999)}`,
      status: 'ACTIVE' as const,
      usageCap: Math.floor(body.usageCap),
      successfulAdmissions: 0,
      activeGuestCount: 0,
      expiresAt: body.expiresAt,
      createdAt: new Date().toISOString(),
      createdBy: 'Nguyễn Minh Quân',
    }
    m03.invites.unshift(created)
    m03.auditLog.unshift({
      id: `aud-${Date.now()}`,
      occurredAt: created.createdAt,
      actorName: 'Nguyễn Minh Quân',
      action: 'CREATE_INVITE',
      targetLabel: `${created.label} (${created.usageCap} lượt)`,
      decision: 'APPLIED',
      reason: 'Tạo liên kết mời bất biến kèm mã QR',
      sessionId: created.sessionId,
    })
    return HttpResponse.json(created, { status: 201 })
  }),

  http.post('/api/mock/v1/invites/:inviteId/revoke', async ({ request, params }) => {
    const role = readRole(request)
    if (role !== 'OWNER') {
      return forbidden('Chỉ Chủ sở hữu mới có quyền thu hồi liên kết mời.')
    }
    await delay(100)
    const m03 = getM03Store(readScenario(request))
    const invite = m03.invites.find((i) => i.id === params.inviteId)
    if (!invite) return HttpResponse.json({ message: 'Không tìm thấy liên kết mời.' }, { status: 404 })

    invite.status = 'REVOKED'
    invite.revokedAt = new Date().toISOString()
    invite.activeGuestCount = 0

    // Eject all active guest sessions admitted via this specific invite only (IM-D4)
    let ejectedCount = 0
    for (const g of m03.guestSessions) {
      if (g.inviteId === invite.id && !g.revoked) {
        g.revoked = true
        g.active = false
        ejectedCount += 1
      }
    }

    m03.auditLog.unshift({
      id: `aud-${Date.now()}`,
      occurredAt: invite.revokedAt,
      actorName: 'Nguyễn Minh Quân',
      action: 'REVOKE_INVITE',
      targetLabel: invite.label,
      decision: 'APPLIED',
      reason: `Thu hồi liên kết và ngắt quyền ${ejectedCount} khách đang xem từ liên kết này`,
      sessionId: invite.sessionId,
    })
    return HttpResponse.json({ invite, ejectedCount })
  }),

  /* ---------- M03-D: Viewer Live Room ---------- */
  http.get('/api/mock/v1/viewer/:sessionId', async ({ request, params }) => {
    await delay(60)
    const url = new URL(request.url)
    const inviteToken = url.searchParams.get('invite')
    const guestSessionId = url.searchParams.get('guestSessionId')
    return HttpResponse.json(
      buildViewerRoomSnapshot(
        readScenario(request),
        String(params.sessionId),
        inviteToken,
        guestSessionId,
      ),
    )
  }),

  http.post('/api/mock/v1/viewer/:sessionId/admit', async ({ request, params }) => {
    await delay(100)
    const scenario = readScenario(request)
    const sessionId = String(params.sessionId)
    const m03 = getM03Store(scenario)
    const body = (await request.json()) as {
      inviteToken: string | null
      nickname: string
      existingGuestSessionId?: string | null
    }

    const nickname = body.nickname.trim()
    if (nickname.length < 2) {
      return HttpResponse.json(
        { message: 'Tên hiển thị cần tối thiểu 2 ký tự.' },
        { status: 400 },
      )
    }

    // Refresh / rejoin with same valid guest session does NOT double-count (VR-D5=A)
    if (body.existingGuestSessionId) {
      const existing = m03.guestSessions.find(
        (g) => g.guestSessionId === body.existingGuestSessionId,
      )
      if (existing && !existing.revoked) {
        return HttpResponse.json(
          buildViewerRoomSnapshot(scenario, sessionId, body.inviteToken, existing.guestSessionId),
        )
      }
    }

    const invite = body.inviteToken
      ? m03.invites.find((i) => i.token === body.inviteToken && i.sessionId === sessionId)
      : m03.invites.find((i) => i.sessionId === sessionId && i.status === 'ACTIVE')

    if (!invite || invite.status !== 'ACTIVE') {
      return HttpResponse.json(
        { message: 'Liên kết mời không còn hiệu lực hoặc đã hết hạn.' },
        { status: 403 },
      )
    }
    if (invite.successfulAdmissions >= invite.usageCap) {
      invite.status = 'EXHAUSTED'
      return HttpResponse.json(
        { message: 'Liên kết mời đã đạt tối đa lượt tham gia.' },
        { status: 403 },
      )
    }

    invite.successfulAdmissions += 1
    invite.activeGuestCount += 1
    if (invite.successfulAdmissions >= invite.usageCap) {
      invite.status = 'EXHAUSTED'
    }

    const guestSession = {
      guestSessionId: `gst-${Date.now()}-${invite.successfulAdmissions}`,
      inviteId: invite.id,
      sessionId,
      nickname,
      admittedAt: new Date().toISOString(),
      active: true,
      revoked: false,
    }
    m03.guestSessions.push(guestSession)

    return HttpResponse.json(
      buildViewerRoomSnapshot(scenario, sessionId, invite.token, guestSession.guestSessionId),
    )
  }),

  http.post('/api/mock/v1/viewer/:sessionId/comments', async ({ request, params }) => {
    await delay(140)
    const scenario = readScenario(request)
    const sessionId = String(params.sessionId)
    const core = getStore(scenario)
    const m03 = getM03Store(scenario)
    const session = core.sessions.find((s) => s.id === sessionId)
    if (!session || session.lifecycle !== 'LIVE') {
      return HttpResponse.json(
        { message: 'Chỉ được gửi bình luận khi phiên đang phát trực tiếp (VR-D3).' },
        { status: 400 },
      )
    }

    const body = (await request.json()) as {
      guestSessionId: string
      nickname: string
      body: string
      clientSubmissionId: string
    }

    const guest = m03.guestSessions.find((g) => g.guestSessionId === body.guestSessionId)
    if (guest?.revoked) {
      return forbidden('Quyền tham gia phòng của bạn đã bị thu hồi.')
    }

    const text = body.body.trim()
    if (!text) {
      return HttpResponse.json({ message: 'Nội dung bình luận không được trống.' }, { status: 400 })
    }
    if (text.toLowerCase().includes('spam') || text.toLowerCase().includes('lừa đảo')) {
      return HttpResponse.json(
        { message: 'Bình luận không phù hợp quy định cộng đồng của phòng xem.' },
        { status: 422 },
      )
    }

    const rt = getOrCreateRuntime(scenario, sessionId)
    if (!m03.processedSubmissionIds.has(body.clientSubmissionId)) {
      m03.processedSubmissionIds.add(body.clientSubmissionId)
      rt.comments.unshift({
        id: `cmt-${Date.now()}`,
        sessionId,
        viewerId: body.guestSessionId,
        nickname: body.nickname,
        body: text,
        receivedAt: new Date().toISOString(),
        moderationStatus: 'ELIGIBLE',
        queueStatus: 'QUEUED',
        priorityScore: 80,
        ttlSeconds: 120,
      })
    }

    return HttpResponse.json({
      receiptStatus: 'RECEIVED',
      commentId: rt.comments[0]?.id,
    })
  }),

  /* ---------- M03-E: Session Reports ---------- */
  http.get('/api/mock/v1/reports/:sessionId', async ({ request, params }) => {
    await delay(70)
    const scenario = readScenario(request)
    const role = readRole(request)
    const sessionId = String(params.sessionId)
    if (!isActorAssignedToSession(scenario, role, sessionId)) {
      return forbidden('Bạn không có quyền xem báo cáo của phiên này.')
    }
    const report = buildSessionReport(scenario, role, sessionId)
    if (!report) return HttpResponse.json({ message: 'Không tìm thấy báo cáo phiên.' }, { status: 404 })
    return HttpResponse.json(report)
  }),
]
