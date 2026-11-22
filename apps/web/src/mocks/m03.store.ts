import type { MockScenarioKey } from '@/types/scenario'
import type { UserRole } from '@/types/auth'
import type {
  AccessAuditEvent,
  ControlRoomSnapshot,
  GuestAdmissionSession,
  LiveCommentItem,
  OperatorInvitation,
  PendingSkuSwitch,
  PublisherState,
  RuntimeCommandRecord,
  SessionReportDetail,
  SpeechTurnPhase,
  SpeechTurnRecord,
  ViewerInviteRecord,
  ViewerRoomSnapshot,
  WorkspaceMember,
} from '@/types/m03'
import type { ConnectionFreshness, DialogueSubstate, ReportStatus } from '@/types/domain'
import { getStore } from '@/mocks/store'
import { computeDurationMinutes, formatClockTime, formatDurationMinutesVi } from '@/lib/format'

interface SessionRuntimeState {
  publisherState: PublisherState
  connectionFreshness: ConnectionFreshness
  dialogueSubstate: DialogueSubstate
  activeSkuId: string
  pendingSwitch: PendingSkuSwitch | null
  comments: LiveCommentItem[]
  currentTurn: SpeechTurnRecord | null
  playbackAckIds: Set<string>
  storyCheckpointIndex: number
  commands: RuntimeCommandRecord[]
}

interface M03StoreState {
  scenarioKey: MockScenarioKey
  members: WorkspaceMember[]
  operatorInvites: OperatorInvitation[]
  auditLog: AccessAuditEvent[]
  invites: ViewerInviteRecord[]
  guestSessions: GuestAdmissionSession[]
  runtimes: Record<string, SessionRuntimeState>
  processedSubmissionIds: Set<string>
}

const SPEECH_PHASE_ORDER: SpeechTurnPhase[] = [
  'PLANNING',
  'VERIFYING',
  'PREPARING_AUDIO',
  'LIP_SYNC',
  'READY',
  'COMMITTED',
  'PLAYING',
  'PLAYBACK_COMPLETED',
]

function buildInitialM03Store(scenario: MockScenarioKey): M03StoreState {
  const members: WorkspaceMember[] = [
    {
      id: 'usr-owner-01',
      displayName: 'Nguyễn Minh Quân',
      email: 'quan.nguyen@muonglat.vn',
      initials: 'MQ',
      role: 'OWNER',
      roleLabel: 'Chủ sở hữu',
      status: 'ACTIVE',
      assignedSessionIds: ['ses-014', 'ses-015', 'ses-013', 'ses-012'],
      revision: 4,
      joinedAt: '2026-10-01T08:00:00Z',
    },
    {
      id: 'usr-op-01',
      displayName: 'Trần Ngọc Lan',
      email: 'lan.tran@muonglat.vn',
      initials: 'NL',
      role: 'OPERATOR',
      roleLabel: 'Vận hành viên',
      status: 'ACTIVE',
      assignedSessionIds: ['ses-014', 'ses-013'],
      revision: 3,
      joinedAt: '2026-10-12T09:30:00Z',
    },
    {
      id: 'usr-op-02',
      displayName: 'Lê Thanh Bình',
      email: 'binh.le@muonglat.vn',
      initials: 'TB',
      role: 'OPERATOR',
      roleLabel: 'Vận hành viên',
      status: 'ACTIVE',
      assignedSessionIds: ['ses-014'],
      revision: 2,
      joinedAt: '2026-10-25T14:00:00Z',
    },
  ]

  const operatorInvites: OperatorInvitation[] = [
    {
      id: 'op-inv-01',
      email: 'minh.pham@muonglat.vn',
      status: 'PENDING',
      expiresAt: '2026-11-28T23:59:00Z',
      invitedBy: 'Nguyễn Minh Quân',
      createdAt: '2026-11-20T10:00:00Z',
    },
    {
      id: 'op-inv-02',
      email: 'cuong.le@muonglat.vn',
      status: 'EXPIRED',
      expiresAt: '2026-11-10T23:59:00Z',
      invitedBy: 'Nguyễn Minh Quân',
      createdAt: '2026-11-03T10:00:00Z',
    },
  ]

  const auditLog: AccessAuditEvent[] = [
    {
      id: 'aud-01',
      occurredAt: '2026-11-21T07:25:00Z',
      actorName: 'Nguyễn Minh Quân',
      action: 'ASSIGN_OPERATORS',
      targetLabel: 'Phiên #014 (Trần Ngọc Lan, Lê Thanh Bình)',
      decision: 'APPLIED',
      reason: 'Phân công 2 Vận hành viên đồng thời theo MP-N1',
      sessionId: 'ses-014',
    },
    {
      id: 'aud-02',
      occurredAt: '2026-11-21T07:30:00Z',
      actorName: 'Nguyễn Minh Quân',
      action: 'START_SESSION',
      targetLabel: 'Phiên #014',
      decision: 'APPLIED',
      reason: 'Toàn bộ điều kiện Readiness đạt và publisher đã xác nhận LIVE',
      sessionId: 'ses-014',
    },
  ]

  const invites: ViewerInviteRecord[] = [
    {
      id: 'inv-doi-tac-01',
      sessionId: 'ses-014',
      sessionCode: 'Phiên #014',
      label: 'Đối tác phân phối',
      token: 'ml014-doitac',
      status: scenario === 'invite-expired' ? 'EXPIRED' : 'ACTIVE',
      usageCap: 20,
      successfulAdmissions: 12,
      activeGuestCount: 8,
      expiresAt: scenario === 'invite-expired' ? '2026-11-20T18:00:00Z' : '2026-11-22T23:00:00Z',
      createdAt: '2026-11-21T07:10:00Z',
      createdBy: 'Nguyễn Minh Quân',
    },
    {
      id: 'inv-dung-thu-02',
      sessionId: 'ses-014',
      sessionCode: 'Phiên #014',
      label: 'Nhóm dùng thử',
      token: 'ml014-dungthu',
      status: 'ACTIVE',
      usageCap: 50,
      successfulAdmissions: 23,
      activeGuestCount: 14,
      expiresAt: '2026-11-23T23:00:00Z',
      createdAt: '2026-11-21T07:12:00Z',
      createdBy: 'Nguyễn Minh Quân',
    },
    {
      id: 'inv-exhausted-03',
      sessionId: 'ses-014',
      sessionCode: 'Phiên #014',
      label: 'Sự kiện trải nghiệm',
      token: 'ml014-sukien',
      status: 'EXHAUSTED',
      usageCap: 100,
      successfulAdmissions: 100,
      activeGuestCount: 0,
      expiresAt: '2026-11-22T23:00:00Z',
      createdAt: '2026-11-19T11:00:00Z',
      createdBy: 'Nguyễn Minh Quân',
    },
    {
      id: 'inv-revoked-04',
      sessionId: 'ses-014',
      sessionCode: 'Phiên #014',
      label: 'Truyền thông nội bộ (Đã thu hồi)',
      token: 'ml014-noibo',
      status: 'REVOKED',
      usageCap: 30,
      successfulAdmissions: 4,
      activeGuestCount: 0,
      expiresAt: '2026-11-25T23:00:00Z',
      createdAt: '2026-11-20T09:00:00Z',
      createdBy: 'Nguyễn Minh Quân',
      revokedAt: '2026-11-21T07:20:00Z',
    },
  ]

  const defaultComments: LiveCommentItem[] = [
    {
      id: 'cmt-01',
      sessionId: 'ses-014',
      viewerId: 'vw-lananh',
      nickname: 'Lan Anh',
      body: 'Mứt mận có vị chua nhiều không và bảo quản được bao lâu?',
      receivedAt: '2026-11-21T08:11:00Z',
      referencedSkuCode: 'ML-001',
      moderationStatus: 'ELIGIBLE',
      queueStatus: 'PRIORITIZED',
      priorityScore: 92,
      ttlSeconds: 120,
    },
    {
      id: 'cmt-02',
      sessionId: 'ses-014',
      viewerId: 'vw-minhduc',
      nickname: 'Minh Đức',
      body: 'Mật ong rừng 500ml có cần để tủ lạnh không shop?',
      receivedAt: '2026-11-21T08:12:30Z',
      referencedSkuCode: 'ML-002',
      moderationStatus: 'ELIGIBLE',
      queueStatus: 'QUEUED',
      priorityScore: 84,
      ttlSeconds: 110,
    },
    {
      id: 'cmt-03',
      sessionId: 'ses-014',
      viewerId: 'vw-thuha',
      nickname: 'Thu Hà',
      body: 'Chuối sấy dẻo có thêm đường tinh luyện không ạ?',
      receivedAt: '2026-11-21T08:13:45Z',
      referencedSkuCode: 'ML-004',
      moderationStatus: 'ELIGIBLE',
      queueStatus: 'QUEUED',
      priorityScore: 76,
      ttlSeconds: 95,
    },
  ]

  const defaultCommands: RuntimeCommandRecord[] =
    scenario === 'command-conflict'
      ? [
          {
            commandId: 'cmd-conf-01',
            type: 'PAUSE_AI',
            actorId: 'usr-op-02',
            actorName: 'Lê Thanh Bình',
            expectedRevision: 42,
            sessionEpoch: 3,
            status: 'APPLIED',
            reason: 'Ưu tiên cao hơn lệnh chuyển SKU cùng phiên bản revision 42',
            requestedAt: '2026-11-21T08:14:10Z',
          },
          {
            commandId: 'cmd-conf-02',
            type: 'SWITCH_SKU',
            actorId: 'usr-op-01',
            actorName: 'Trần Ngọc Lan',
            expectedRevision: 42,
            sessionEpoch: 3,
            status: 'REJECTED',
            reason: 'Xung đột revision (409): trạng thái phiên đã cập nhật lên revision 43',
            requestedAt: '2026-11-21T08:14:11Z',
          },
        ]
      : []

  const runtime014: SessionRuntimeState = {
    publisherState: scenario === 'media-degraded' ? 'DEGRADED' : 'CONNECTED',
    connectionFreshness: 'CONNECTED',
    dialogueSubstate: scenario === 'ai-paused' ? 'IDLE' : 'PLAYING_SCRIPT',
    activeSkuId: 'sku-ml-001',
    pendingSwitch: null,
    comments: defaultComments,
    currentTurn: {
      turnId: 'turn-014-05',
      commentId: 'cmt-01',
      skuCode: 'ML-001',
      safeSummary:
        'Giải đáp cách bảo quản Mứt Mận Mường Lát nơi khô mát, hạn dùng 12 tháng và giá niêm yết 118.000 đ/túi 500g.',
      sourceRef: 'Ho_so_san_pham_Mut_Man_v2.pdf · Trang 1 & 2',
      phase: 'READY',
      updatedAt: '2026-11-21T08:14:50Z',
    },
    playbackAckIds: new Set([
      'ack-014-01',
      'ack-014-02',
      'ack-014-03',
      'ack-014-04',
    ]),
    storyCheckpointIndex: 2,
    commands: defaultCommands,
  }

  return {
    scenarioKey: scenario,
    members,
    operatorInvites,
    auditLog,
    invites,
    guestSessions: [],
    runtimes: {
      'ses-014': runtime014,
    },
    processedSubmissionIds: new Set(),
  }
}

let m03Store: M03StoreState = buildInitialM03Store('happy-path')

export function getM03Store(scenario: MockScenarioKey): M03StoreState {
  if (m03Store.scenarioKey !== scenario) {
    m03Store = buildInitialM03Store(scenario)
  }
  return m03Store
}

export function resetM03Store(scenario: MockScenarioKey): M03StoreState {
  m03Store = buildInitialM03Store(scenario)
  return m03Store
}

export function getOrCreateRuntime(
  scenario: MockScenarioKey,
  sessionId: string,
): SessionRuntimeState {
  const m03 = getM03Store(scenario)
  if (!m03.runtimes[sessionId]) {
    const core = getStore(scenario)
    const session = core.sessions.find((s) => s.id === sessionId)
    m03.runtimes[sessionId] = {
      publisherState: 'CONNECTED',
      connectionFreshness: 'CONNECTED',
      dialogueSubstate: 'PLAYING_SCRIPT',
      activeSkuId: session?.selectedSkuIds[0] ?? 'sku-ml-001',
      pendingSwitch: null,
      comments: [],
      currentTurn: null,
      playbackAckIds: new Set(),
      storyCheckpointIndex: 1,
      commands: [],
    }
  }
  return m03.runtimes[sessionId]
}

export function isActorAssignedToSession(
  scenario: MockScenarioKey,
  role: UserRole,
  sessionId: string,
): boolean {
  if (role === 'OWNER') return true
  const m03 = getM03Store(scenario)
  const op = m03.members.find((m) => m.id === 'usr-op-01')
  return Boolean(
    op && op.status === 'ACTIVE' && op.assignedSessionIds.includes(sessionId),
  )
}

export function buildControlRoomSnapshot(
  scenario: MockScenarioKey,
  role: UserRole,
  sessionId: string,
): ControlRoomSnapshot | null {
  const core = getStore(scenario)
  const m03 = getM03Store(scenario)
  const session = core.sessions.find((s) => s.id === sessionId)
  if (!session) return null

  const rt = getOrCreateRuntime(scenario, sessionId)
  const canOperate = isActorAssignedToSession(scenario, role, sessionId)
  const sessionSkus = session.selectedSkuIds
    .map((skuId) => core.products.find((p) => p.skuId === skuId))
    .filter((p): p is NonNullable<typeof p> => Boolean(p))
    .map((p) => ({
      skuId: p.skuId,
      skuCode: p.skuCode,
      name: p.name,
      priceVnd: p.priceVnd,
      eligible: p.ocopStatus === 'VERIFIED' && p.knowledgeStatus === 'APPROVED',
      blockerReason:
        p.ocopStatus !== 'VERIFIED'
          ? 'OCOP chưa được xác minh'
          : p.knowledgeStatus !== 'APPROVED'
            ? 'Tri thức chưa được duyệt'
            : undefined,
    }))

  const activeSku =
    sessionSkus.find((s) => s.skuId === rt.activeSkuId) ?? sessionSkus[0]
  const nextSku = sessionSkus.find((s) => s.skuId !== activeSku?.skuId)
  const activeInvite = m03.invites.find(
    (inv) => inv.sessionId === sessionId && inv.status === 'ACTIVE',
  )
  const story = core.storyPlans[sessionId]

  return {
    sessionId: session.id,
    sessionCode: session.code,
    sessionTitle: session.title,
    revision: session.revision,
    epoch: session.epoch,
    lifecycle: session.lifecycle,
    aiState: session.aiState,
    mediaHealth: session.mediaHealth,
    publisherState: rt.publisherState,
    connectionFreshness: rt.connectionFreshness,
    dialogueSubstate: rt.dialogueSubstate,
    presenterId: session.presenterId,
    presenterName: session.presenterName,
    fallbackModeLabel:
      session.mediaHealth === 'DEGRADED'
        ? session.fallbackDescription || 'Đang dùng cảnh sản phẩm dự phòng + âm thanh xác minh'
        : undefined,
    activeSkuId: activeSku?.skuId ?? 'sku-ml-001',
    activeSkuCode: activeSku?.skuCode ?? 'ML-001',
    activeSkuName: activeSku?.name ?? 'Mứt Mận Mường Lát',
    activeSkuPriceVnd: activeSku?.priceVnd ?? 118000,
    nextSkuName: nextSku?.name,
    pendingSwitch: rt.pendingSwitch,
    sessionSkus,
    comments: rt.comments,
    currentTurn: rt.currentTurn,
    completedTurnsCount: rt.playbackAckIds.size,
    storyCheckpointIndex: rt.storyCheckpointIndex,
    storyTotalArcs: story?.arcs.length ?? 4,
    commands: rt.commands,
    canOperate,
    canCopyInvite: role === 'OWNER' && Boolean(activeInvite),
    activeInviteUrl: activeInvite
      ? `/live/${sessionId}?invite=${activeInvite.token}`
      : undefined,
    isMockRuntime: true,
  }
}

export function advanceSpeechTurnPhase(
  scenario: MockScenarioKey,
  sessionId: string,
): SpeechTurnRecord | null {
  const rt = getOrCreateRuntime(scenario, sessionId)
  if (!rt.currentTurn) return null
  const idx = SPEECH_PHASE_ORDER.indexOf(rt.currentTurn.phase)
  if (idx === -1 || idx >= SPEECH_PHASE_ORDER.length - 1) return rt.currentTurn
  const nextPhase = SPEECH_PHASE_ORDER[idx + 1]
  rt.currentTurn.phase = nextPhase
  rt.currentTurn.updatedAt = new Date().toISOString()

  if (nextPhase === 'COMMITTED' && rt.currentTurn.commentId) {
    const c = rt.comments.find((x) => x.id === rt.currentTurn?.commentId)
    if (c) c.queueStatus = 'COMMITTED'
  }
  if (nextPhase === 'PLAYBACK_COMPLETED') {
    const ackId = `ack-${rt.currentTurn.turnId}`
    rt.currentTurn.playbackAckId = ackId
    if (!rt.playbackAckIds.has(ackId)) {
      rt.playbackAckIds.add(ackId)
      rt.storyCheckpointIndex += 1
    }
    if (rt.currentTurn.commentId) {
      const c = rt.comments.find((x) => x.id === rt.currentTurn?.commentId)
      if (c) c.queueStatus = 'PLAYED'
    }
  }
  return rt.currentTurn
}

export function buildViewerRoomSnapshot(
  scenario: MockScenarioKey,
  sessionId: string,
  inviteToken: string | null,
  guestSessionId: string | null,
): ViewerRoomSnapshot {
  const core = getStore(scenario)
  const m03 = getM03Store(scenario)
  const session = core.sessions.find((s) => s.id === sessionId) ?? core.sessions[0]
  const rt = getOrCreateRuntime(scenario, session?.id ?? sessionId)

  const invite = inviteToken
    ? m03.invites.find((i) => i.token === inviteToken && i.sessionId === (session?.id ?? sessionId))
    : m03.invites.find((i) => i.sessionId === (session?.id ?? sessionId) && i.status === 'ACTIVE')

  const guest = guestSessionId
    ? m03.guestSessions.find((g) => g.guestSessionId === guestSessionId) ?? null
    : null

  let accessState: ViewerRoomSnapshot['accessState'] = 'VALID'
  let accessReason: string | undefined

  if (guest?.revoked) {
    accessState = 'REVOKED'
    accessReason = 'Liên kết mời của bạn vừa bị Chủ sở hữu thu hồi. Quyền xem phòng livestream đã kết thúc.'
  } else if (!invite) {
    accessState = 'INVALID'
    accessReason = 'Liên kết mời không hợp lệ hoặc không tồn tại.'
  } else if (invite.status === 'REVOKED') {
    accessState = 'REVOKED'
    accessReason = 'Lời mời này đã bị thu hồi bởi người tổ chức.'
  } else if (invite.status === 'EXPIRED') {
    accessState = 'EXPIRED'
    accessReason = 'Lời mời đã hết thời hạn sử dụng. Vui lòng liên hệ người mời.'
  } else if (invite.status === 'EXHAUSTED' && !guest) {
    accessState = 'EXHAUSTED'
    accessReason = 'Liên kết mời đã đạt giới hạn số lượt tham gia.'
  }

  const activeProd = core.products.find((p) => p.skuId === rt.activeSkuId) ?? core.products[0]

  return {
    accessState,
    accessReason,
    inviteId: invite?.id,
    inviteLabel: invite?.label,
    sessionId: session?.id ?? sessionId,
    sessionTitle: session?.title ?? 'Giới thiệu đặc sản Mường Lát',
    merchantName: 'Đặc sản Mường Lát',
    lifecycle: session?.lifecycle ?? 'LIVE',
    mediaHealth: session?.mediaHealth ?? 'HEALTHY',
    presenterId: session?.presenterId ?? 'prs-linh-01',
    presenterName: session?.presenterName ?? 'Linh — Đặc sản vùng cao',
    activeSku: activeProd
      ? {
          skuId: activeProd.skuId,
          skuCode: activeProd.skuCode,
          name: activeProd.name,
          priceVnd: activeProd.priceVnd,
          packSpec: activeProd.packSpec,
          ocopVerified: activeProd.ocopStatus === 'VERIFIED',
          ocopStars: activeProd.ocopStars,
        }
      : null,
    comments: rt.comments
      .filter((c) => c.moderationStatus === 'ELIGIBLE')
      .map((c) => ({
        id: c.id,
        nickname: c.nickname,
        body: c.body,
        receivedAt: c.receivedAt,
      })),
    guestSession: guest,
    revision: session?.revision ?? 1,
  }
}

function addMinutesIso(baseIso: string, minutes: number): string {
  return new Date(new Date(baseIso).getTime() + minutes * 60000).toISOString()
}

function distributeAdmissions(total: number, weights: number[]): number[] {
  if (total <= 0 || weights.length === 0) return weights.map(() => 0)
  const weightSum = weights.reduce((a, b) => a + b, 0)
  const raw = weights.map((w) => Math.floor((total * w) / weightSum))
  let remainder = total - raw.reduce((a, b) => a + b, 0)
  let idx = 0
  while (remainder > 0) {
    raw[idx % raw.length] += 1
    remainder -= 1
    idx += 1
  }
  return raw
}

export function resolveSessionReportStatus(
  sessionId: string,
  lifecycle: string,
  scenario: MockScenarioKey,
): ReportStatus {
  if (lifecycle === 'FAILED') return 'FAILED'
  if (lifecycle === 'CREATED' || lifecycle === 'PREPARING' || lifecycle === 'READY' || lifecycle === 'CANCELLED') {
    return 'PENDING'
  }
  if (scenario === 'report-partial' || sessionId === 'ses-013') {
    return 'PARTIAL'
  }
  return 'READY'
}

export function buildSessionReport(
  scenario: MockScenarioKey,
  role: UserRole,
  sessionId: string,
): SessionReportDetail | null {
  const core = getStore(scenario)
  const m03 = getM03Store(scenario)
  const session = core.sessions.find((s) => s.id === sessionId)
  if (!session) return null

  const rt = getOrCreateRuntime(scenario, sessionId)
  const reportStatus = resolveSessionReportStatus(sessionId, session.lifecycle, scenario)
  const isPending = reportStatus === 'PENDING'
  const isPartial = reportStatus === 'PARTIAL'
  const isReduced = role === 'OPERATOR'

  const sessionInvites = m03.invites.filter((i) => i.sessionId === sessionId)
  const inviteAdmissions = sessionInvites.reduce((sum, inv) => sum + inv.successfulAdmissions, 0)
  const totalAdmissions = isPending
    ? null
    : inviteAdmissions > 0
      ? inviteAdmissions
      : sessionId === 'ses-013'
        ? 86
        : sessionId === 'ses-012'
          ? 54
          : 0

  const playedAck = isPending
    ? null
    : sessionId === 'ses-013'
      ? 37
      : sessionId === 'ses-012'
        ? 29
        : rt.playbackAckIds.size

  const commentsReceived = isPending
    ? null
    : sessionId === 'ses-013'
      ? 143
      : sessionId === 'ses-012'
        ? 92
        : rt.comments.length

  const startIso = session.startedAt
  const endIso =
    session.stoppedAt ??
    (startIso && session.lifecycle === 'LIVE' ? session.updatedAt : undefined)
  const durationMinutes = computeDurationMinutes(startIso, endIso)
  const durationLabel = formatDurationMinutesVi(durationMinutes)

  const rawAudit = m03.auditLog.filter((a) => !a.sessionId || a.sessionId === sessionId)
  const maskedAudit = isReduced
    ? rawAudit.map((a) => ({
        ...a,
        actorName: a.actorName === 'Nguyễn Minh Quân' ? 'Chủ sở hữu (Ẩn danh tính)' : a.actorName,
      }))
    : rawAudit

  let intervalChart: SessionReportDetail['intervalChart'] = []
  let timeline: SessionReportDetail['timeline'] = []
  let chartCoverageLabel = 'Chưa có dữ liệu phát sóng (phiên chưa bắt đầu)'

  if (!isPending && startIso) {
    if (sessionId === 'ses-013') {
      // Canonical 19:00 -> 20:32 (UTC 12:00 -> 13:32), 7 x 15-min buckets summing to exactly 86
      const bucketAdmissions = [10, 16, 22, 15, 11, 8, 4]
      intervalChart = bucketAdmissions.map((count, idx) => {
        const iso = addMinutesIso(startIso, idx * 15)
        return {
          bucketStartIso: iso,
          bucketLabel: formatClockTime(iso),
          admissions: count,
          concurrentViewers: null,
        }
      })
      chartCoverageLabel = `Toàn bộ phiên (${formatClockTime(startIso)} – ${formatClockTime(endIso ?? addMinutesIso(startIso, 92))}) · Tổng 7 khung = 86 lượt khớp KPI`
      timeline = [
        {
          id: 'tl-13-1',
          occurredAtIso: startIso,
          timeLabel: formatClockTime(startIso),
          title: 'Bắt đầu phát trực tiếp (LIVE)',
          kind: 'LIVE',
          detail: 'Publisher đã xác nhận luồng phát ổn định.',
        },
        {
          id: 'tl-13-2',
          occurredAtIso: addMinutesIso(startIso, 22),
          timeLabel: formatClockTime(addMinutesIso(startIso, 22)),
          title: 'Tạm dừng AI (AI PAUSED)',
          kind: 'AI_PAUSED',
          detail: 'Stream vẫn duy trì cảnh sản phẩm an toàn.',
        },
        {
          id: 'tl-13-3',
          occurredAtIso: addMinutesIso(startIso, 34),
          timeLabel: formatClockTime(addMinutesIso(startIso, 34)),
          title: 'Media suy giảm tạm thời',
          kind: 'MEDIA_DEGRADED',
          detail: 'Chuyển sang cảnh sản phẩm dự phòng + âm thanh xác minh.',
        },
        {
          id: 'tl-13-4',
          occurredAtIso: addMinutesIso(startIso, 42),
          timeLabel: formatClockTime(addMinutesIso(startIso, 42)),
          title: 'Media phục hồi ổn định',
          kind: 'LIVE',
          detail: 'Quay lại cảnh AI Presenter bình thường.',
        },
        {
          id: 'tl-13-5',
          occurredAtIso: endIso ?? addMinutesIso(startIso, 92),
          timeLabel: formatClockTime(endIso ?? addMinutesIso(startIso, 92)),
          title: 'Kết thúc phiên an toàn (STOPPED)',
          kind: 'STOPPED',
          detail: 'Phiên khép lại sau 1 giờ 32 phút phát thực tế.',
        },
      ]
    } else if (sessionId === 'ses-012') {
      // Canonical 20:00 -> 21:15 (UTC 13:00 -> 14:15), 5 x 15-min buckets summing to 54
      const bucketAdmissions = [9, 14, 15, 10, 6]
      const concurrent = [7, 15, 24, 19, 11]
      intervalChart = bucketAdmissions.map((count, idx) => {
        const iso = addMinutesIso(startIso, idx * 15)
        return {
          bucketStartIso: iso,
          bucketLabel: formatClockTime(iso),
          admissions: count,
          concurrentViewers: isPartial ? null : concurrent[idx],
        }
      })
      chartCoverageLabel = `Toàn bộ phiên (${formatClockTime(startIso)} – ${formatClockTime(endIso ?? addMinutesIso(startIso, 75))}) · Tổng 5 khung = 54 lượt khớp KPI`
      timeline = [
        {
          id: 'tl-12-1',
          occurredAtIso: startIso,
          timeLabel: formatClockTime(startIso),
          title: 'Bắt đầu phát trực tiếp (LIVE)',
          kind: 'LIVE',
          detail: 'Publisher xác nhận luồng phát ổn định.',
        },
        {
          id: 'tl-12-2',
          occurredAtIso: endIso ?? addMinutesIso(startIso, 75),
          timeLabel: formatClockTime(endIso ?? addMinutesIso(startIso, 75)),
          title: 'Kết thúc phiên an toàn (STOPPED)',
          kind: 'STOPPED',
          detail: 'Phiên kết thúc bình thường không có sự cố media.',
        },
      ]
    } else {
      // Dynamic session (e.g. ses-014): derive buckets strictly from canonical startIso & totalAdmissions
      const bucketCounts = distributeAdmissions(totalAdmissions ?? 0, [15, 25, 30, 18, 12])
      const concurrentSamples = [8, 19, 28, 22, 15]
      intervalChart = bucketCounts.map((count, idx) => {
        const iso = addMinutesIso(startIso, idx * 15)
        return {
          bucketStartIso: iso,
          bucketLabel: formatClockTime(iso),
          admissions: count,
          concurrentViewers: isPartial ? null : concurrentSamples[idx],
        }
      })
      chartCoverageLabel = `Toàn bộ phiên tính từ ${formatClockTime(startIso)} · Tổng ${intervalChart.length} khung = ${totalAdmissions ?? 0} lượt khớp KPI`
      timeline = [
        {
          id: `tl-${session.id}-1`,
          occurredAtIso: startIso,
          timeLabel: formatClockTime(startIso),
          title: 'Bắt đầu phát trực tiếp (LIVE)',
          kind: 'LIVE',
          detail: 'Publisher đã xác nhận luồng phát ổn định.',
        },
        ...(session.lifecycle === 'STOPPED' && endIso
          ? [
              {
                id: `tl-${session.id}-end`,
                occurredAtIso: endIso,
                timeLabel: formatClockTime(endIso),
                title: 'Kết thúc phiên (STOPPED)',
                kind: 'STOPPED' as const,
                detail: 'Phiên livestream đã kết thúc theo xác nhận hệ thống.',
              },
            ]
          : []),
      ]
    }
  }

  const peakConcurrent =
    isPending || isPartial
      ? null
      : Math.max(0, ...intervalChart.map((pt) => pt.concurrentViewers ?? 0))

  const generatedAt = session.stoppedAt ?? session.updatedAt

  return {
    sessionId: session.id,
    sessionCode: session.code,
    sessionTitle: session.title,
    lifecycle: session.lifecycle,
    reportStatus,
    startedAt: startIso,
    stoppedAt: session.stoppedAt,
    generatedAt,
    chartCoverageLabel,
    isReducedOperatorView: isReduced,
    canExport: role === 'OWNER' && reportStatus === 'READY',
    kpis: [
      {
        key: 'live_duration_seconds',
        label: 'Thời lượng phát LIVE',
        value: isPending ? null : durationLabel,
        unit: '',
        status: isPending ? 'NOT_AVAILABLE' : 'MEASURED',
        source: 'Hệ thống quản lý phiên phát',
        reason: isPending ? 'Phiên chưa bắt đầu phát trực tiếp.' : undefined,
      },
      {
        key: 'guest_successful_admissions',
        label: 'Lượt vào phòng thành công',
        value: totalAdmissions,
        unit: isPending ? '' : 'lượt',
        status: isPending ? 'NOT_AVAILABLE' : 'MEASURED',
        source: 'Hệ thống ghi nhận lượt vào phòng',
        reason: isPending ? 'Chưa phát sinh lượt cấp quyền tham gia.' : undefined,
      },
      {
        key: 'comments_received',
        label: 'Bình luận đã tiếp nhận',
        value: commentsReceived,
        unit: isPending ? '' : 'bình luận',
        status: isPending ? 'NOT_AVAILABLE' : 'MEASURED',
        source: 'Hệ thống tiếp nhận bình luận',
        reason: isPending ? 'Chưa mở phòng bình luận.' : undefined,
      },
      {
        key: 'answered_played',
        label: 'Câu AI đã phát xong',
        value: playedAck,
        unit: isPending ? '' : 'lượt phát',
        status: isPending ? 'NOT_AVAILABLE' : 'MEASURED',
        source: 'Xác nhận nội dung đã phát tới người xem',
        reason: isPending ? 'Chưa có lượt phát AI nào được xác nhận đã phát xong.' : undefined,
      },
      {
        key: 'concurrent_viewers',
        label: 'Người xem đồng thời cao nhất',
        value: peakConcurrent,
        unit: peakConcurrent === null ? '' : 'người',
        status: peakConcurrent === null ? 'NOT_AVAILABLE' : 'MEASURED',
        source: 'Dữ liệu theo dõi người xem trực tiếp',
        reason:
          peakConcurrent === null
            ? isPending
              ? 'Phiên chưa phát trực tiếp nên chưa có dữ liệu người xem đồng thời.'
              : 'Chưa thu thập đủ mẫu theo dõi người xem theo khung thời gian cho phiên này (không suy luận từ lượt vào phòng và không thay bằng 0).'
            : undefined,
      },
    ],
    intervalChart,
    hasConcurrentTelemetry: !isPending && !isPartial,
    timeline,
    aiFunnel: {
      commentsReceived: commentsReceived ?? 0,
      commentsEligible: isPending
        ? 0
        : sessionId === 'ses-013'
          ? 118
          : sessionId === 'ses-012'
            ? 76
            : rt.comments.filter((c) => c.moderationStatus === 'ELIGIBLE').length,
      turnsPrepared: isPending
        ? 0
        : sessionId === 'ses-013'
          ? 44
          : sessionId === 'ses-012'
            ? 33
            : (playedAck ?? 0) + 1,
      turnsCommitted: isPending
        ? 0
        : sessionId === 'ses-013'
          ? 39
          : sessionId === 'ses-012'
            ? 31
            : (playedAck ?? 0) + 1,
      turnsPlayedAck: playedAck ?? 0,
      dedupedAckCount: isPending ? 0 : 2,
    },
    mediaIncidents:
      sessionId === 'ses-013' && startIso
        ? [
            {
              id: 'inc-13-1',
              timeLabel: `${formatClockTime(addMinutesIso(startIso, 34))} – ${formatClockTime(addMinutesIso(startIso, 42))}`,
              severity: 'warning',
              summary: 'Độ trễ lip-sync vượt ngưỡng mục tiêu trong 8 phút',
              fallbackUsed: 'PRODUCT_SHOWCASE + verified audio',
            },
          ]
        : [],
    auditEvents: maskedAudit,
  }
}
