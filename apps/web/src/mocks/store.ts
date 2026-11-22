import type { MockScenarioKey } from '@/types/scenario'
import type { UserRole } from '@/types/auth'
import type {
  KnowledgePackageDetail,
  OnboardingDraft,
  PresenterDetail,
  ProductDetail,
  ReadinessGateItem,
  ReadinessSnapshot,
  SessionDetail,
  StoryPlanDetail,
} from '@/types/m02'
import {
  createInitialKnowledge,
  createInitialOnboardingDraft,
  createInitialPresenters,
  createInitialProducts,
  createInitialSessions,
  createInitialStoryPlans,
} from '@/mocks/fixtures/m02.fixtures'
import { buildDashboardSnapshot } from '@/mocks/fixtures/dashboard.fixtures'
import type { DashboardSnapshot } from '@/features/dashboard/types/dashboard.types'

interface MockStoreState {
  scenarioKey: MockScenarioKey
  presenters: PresenterDetail[]
  products: ProductDetail[]
  knowledge: KnowledgePackageDetail[]
  storyPlans: Record<string, StoryPlanDetail>
  sessions: SessionDetail[]
  onboarding: OnboardingDraft
  mediaReadyMock: boolean
}

let store: MockStoreState = buildStoreForScenario('happy-path')

function applyScenarioOverrides(
  state: MockStoreState,
  scenario: MockScenarioKey,
): MockStoreState {
  const ses014 = state.sessions.find((s) => s.id === 'ses-014')
  const ses015 = state.sessions.find((s) => s.id === 'ses-015')
  const linh = state.presenters.find((p) => p.id === 'prs-linh-01')

  if (scenario === 'empty') {
    state.presenters = []
    state.products = []
    state.knowledge = []
    state.sessions = []
    state.storyPlans = {}
    state.onboarding.step = 1
  }

  if (scenario === 'ai-paused' && ses014) {
    ses014.aiState = 'PAUSED'
    ses014.mediaHealth = 'HEALTHY'
  }

  if (scenario === 'media-degraded' && ses014) {
    ses014.mediaHealth = 'DEGRADED'
    ses014.fallbackDescription =
      'Đang dùng cảnh sản phẩm dự phòng + âm thanh xác minh'
  }

  if (scenario === 'rights-revoked' && linh) {
    linh.rightsStatus = 'REVOKED'
    linh.rightsConsent.status = 'REVOKED'
    linh.rightsConsent.rightsVersion += 1
    linh.jobStageLabel = 'Bị khóa do thu hồi quyền sử dụng'
  }

  if (scenario === 'verification-pending' && ses015) {
    // Keep ML-003 pending OCOP in #015 so readiness is blocked
    ses015.lifecycle = 'PREPARING'
  }

  recomputeAllSessionReadiness(state)
  return state
}

function buildStoreForScenario(scenario: MockScenarioKey): MockStoreState {
  const initial: MockStoreState = {
    scenarioKey: scenario,
    presenters: createInitialPresenters(),
    products: createInitialProducts(),
    knowledge: createInitialKnowledge(),
    storyPlans: createInitialStoryPlans(),
    sessions: createInitialSessions(),
    onboarding: createInitialOnboardingDraft(),
    mediaReadyMock: true,
  }
  return applyScenarioOverrides(initial, scenario)
}

export function getStore(scenario: MockScenarioKey): MockStoreState {
  if (store.scenarioKey !== scenario) {
    store = buildStoreForScenario(scenario)
  }
  return store
}

export function resetStore(scenario: MockScenarioKey): MockStoreState {
  store = buildStoreForScenario(scenario)
  return store
}

export function computeReadiness(
  state: MockStoreState,
  sessionId: string,
): ReadinessSnapshot | null {
  const session = state.sessions.find((s) => s.id === sessionId)
  if (!session) return null

  const presenter = state.presenters.find((p) => p.id === session.presenterId)
  const selectedProducts = session.selectedSkuIds
    .map((id) => state.products.find((p) => p.skuId === id))
    .filter((p): p is ProductDetail => Boolean(p))
  const story = state.storyPlans[session.id]

  const gates: ReadinessGateItem[] = []

  // 1. Presenter Rights
  const rightsPass = presenter?.rightsStatus === 'VERIFIED'
  gates.push({
    id: 'gate-rights',
    label: 'Quyền sử dụng hình ảnh & giọng nói (Rights Consent)',
    status: rightsPass ? 'PASS' : 'BLOCKED',
    reason: rightsPass
      ? `Quyền của ${presenter?.displayName} đang hợp lệ (v${presenter?.rightsConsent.rightsVersion}).`
      : presenter
        ? `Quyền của ${presenter.displayName} hiện ở trạng thái không hợp lệ hoặc đã bị thu hồi.`
        : 'Chưa chọn AI Presenter hợp lệ cho phiên.',
    sourceLabel: 'Hệ thống xác nhận quyền hình ảnh (Mô phỏng)',
    remediationLabel: 'Mở AI Presenter Studio',
    remediationRoute: presenter
      ? `/studio/presenters/${presenter.id}`
      : '/studio/presenters',
  })

  // 2. Presenter Approval & QC
  const presenterApproved =
    presenter?.approvalStatus === 'APPROVED' && presenter.qcStatus === 'PASS'
  gates.push({
    id: 'gate-presenter-qc',
    label: 'AI Presenter đã qua QC & Chủ sở hữu duyệt',
    status: presenterApproved ? 'PASS' : 'BLOCKED',
    reason: presenterApproved
      ? `${presenter?.displayName} · Gói ${presenter?.activePackVersion} đạt QC và đã được duyệt.`
      : 'Presenter chưa có gói clip đạt QC hoặc chưa được Chủ sở hữu phê duyệt.',
    sourceLabel: 'Thư viện AI Presenter',
    remediationLabel: 'Kiểm duyệt Presenter',
    remediationRoute: presenter
      ? `/studio/presenters/${presenter.id}`
      : '/studio/presenters',
  })

  // 3. Selected SKUs (2–5)
  const skuCountValid =
    selectedProducts.length >= 2 && selectedProducts.length <= 5
  gates.push({
    id: 'gate-sku-count',
    label: 'Danh sách sản phẩm trong phiên (2–5 SKU)',
    status: skuCountValid ? 'PASS' : 'BLOCKED',
    reason: skuCountValid
      ? `Đã chọn ${selectedProducts.length} SKU hợp lệ cho phiên.`
      : `Hiện có ${selectedProducts.length} SKU — MVP yêu cầu từ 2 đến 5 SKU.`,
    sourceLabel: 'Thiết lập phiên livestream',
    remediationLabel: 'Chỉnh sửa SKU phiên',
    remediationRoute: `/studio/sessions/${session.id}/setup`,
  })

  // 4. OCOP Eligibility (Independent P09)
  const unverifiedOcop = selectedProducts.filter((p) => p.ocopStatus !== 'VERIFIED')
  const ocopPass = skuCountValid && unverifiedOcop.length === 0
  gates.push({
    id: 'gate-ocop',
    label: 'Xác minh OCOP độc lập cho toàn bộ SKU',
    status: ocopPass ? 'PASS' : unverifiedOcop.some((p) => p.ocopStatus === 'PENDING_REVIEW') ? 'PENDING' : 'BLOCKED',
    reason: ocopPass
      ? `Toàn bộ ${selectedProducts.length}/${selectedProducts.length} SKU đã có xác minh OCOP hợp lệ.`
      : `${unverifiedOcop.map((p) => p.skuCode).join(', ')} chưa đạt OCOP đã xác minh (không tự suy diễn từ duyệt tri thức).`,
    sourceLabel: 'Hệ thống xác minh OCOP',
    remediationLabel: 'Mở Sản phẩm & OCOP',
    remediationRoute: unverifiedOcop[0]
      ? `/studio/products/${unverifiedOcop[0].skuId}?tab=ocop`
      : '/studio/products',
  })

  // 5. Knowledge & Claims Approval (P05)
  const unapprovedKnowledge = selectedProducts.filter((p) => {
    const pkg = state.knowledge.find((k) => k.skuId === p.skuId)
    return !pkg || pkg.approvalStatus !== 'APPROVED'
  })
  const knowledgePass = skuCountValid && unapprovedKnowledge.length === 0
  gates.push({
    id: 'gate-knowledge',
    label: 'Tri thức & Claims đã được Chủ sở hữu phê duyệt',
    status: knowledgePass ? 'PASS' : 'BLOCKED',
    reason: knowledgePass
      ? 'Toàn bộ SKU đã có phiên bản tri thức đã duyệt và liên kết bằng chứng.'
      : `${unapprovedKnowledge.map((p) => p.skuCode).join(', ')} chưa có gói tri thức được duyệt.`,
    sourceLabel: 'Kho Tri thức & Claims',
    remediationLabel: 'Rà soát Tri thức',
    remediationRoute: unapprovedKnowledge[0]
      ? `/studio/knowledge/${unapprovedKnowledge[0].skuId}`
      : '/studio/knowledge',
  })

  // 6. Story Plan Revision Approval
  const storyPass = story?.approvalStatus === 'APPROVED'
  gates.push({
    id: 'gate-story',
    label: 'Kịch bản Story Plan đã được Chủ sở hữu duyệt',
    status: storyPass ? 'PASS' : 'BLOCKED',
    reason: storyPass
      ? `Đã duyệt phiên bản kịch bản v${story.approvedRevision} (${story.arcs.length} đoạn).`
      : story?.dirtyReason || 'Kịch bản đang ở trạng thái nháp hoặc cần duyệt lại sau khi chỉnh sửa.',
    sourceLabel: 'Kế hoạch nội dung',
    remediationLabel: 'Mở Story Planner',
    remediationRoute: `/studio/sessions/${session.id}/story`,
  })

  // 7. Media & Safe Scene Readiness (Mock)
  gates.push({
    id: 'gate-media',
    label: 'Hạ tầng phát & cảnh dự phòng an toàn (Mô phỏng)',
    status: state.mediaReadyMock ? 'PASS' : 'BLOCKED',
    reason: state.mediaReadyMock
      ? 'Phòng riêng phát sóng mô phỏng và cảnh sản phẩm dự phòng đã sẵn sàng.'
      : 'Bộ phát media mô phỏng chưa sẵn sàng.',
    sourceLabel: 'Hạ tầng phát sóng (Mô phỏng)',
  })

  const blockedCount = gates.filter((g) => g.status === 'BLOCKED').length
  const pendingCount = gates.filter((g) => g.status === 'PENDING').length
  const overallReady = blockedCount === 0 && pendingCount === 0

  return {
    sessionId: session.id,
    sessionCode: session.code,
    sessionTitle: session.title,
    sessionLifecycle: session.lifecycle,
    overallReady,
    blockedCount,
    pendingCount,
    checkedAt: '2026-11-21T08:20:00Z',
    revision: session.revision,
    gates,
  }
}

export function recomputeAllSessionReadiness(state: MockStoreState): void {
  for (const session of state.sessions) {
    const snap = computeReadiness(state, session.id)
    if (!snap) continue
    session.readinessOverall = snap.overallReady ? 'READY' : 'BLOCKED'
    session.readinessBlockedCount = snap.blockedCount + snap.pendingCount
    const story = state.storyPlans[session.id]
    if (story) {
      session.storyApprovalStatus = story.approvalStatus
    }
    if (session.lifecycle === 'PREPARING' && snap.overallReady) {
      session.lifecycle = 'READY'
    } else if (session.lifecycle === 'READY' && !snap.overallReady) {
      session.lifecycle = 'PREPARING'
    }
  }
}

/**
 * Projects Dashboard snapshot directly from the canonical store (fixes M01-FIX-01 & M01-FIX-04).
 */
export function buildSyncedDashboardSnapshot(
  scenario: MockScenarioKey,
  role: UserRole,
): DashboardSnapshot {
  const state = getStore(scenario)
  const base = buildDashboardSnapshot(scenario, role)

  if (scenario === 'empty') {
    return base
  }

  const isOwner = role === 'OWNER'
  const visibleSessions = isOwner
    ? state.sessions
    : state.sessions.filter((s) => s.assignedOperatorIds.includes('usr-op-01'))

  // Synchronize featuredSession and recentSessions from the exact same canonical list (M01-FIX-01)
  const syncedFeatured = base.featuredSession
    ? (visibleSessions.find((s) => s.id === base.featuredSession?.id) ?? visibleSessions[0] ?? null)
    : null

  const syncedRecent = visibleSessions.slice(0, 3)

  // Synchronize Asset Cards KPI counts directly with store entities (M01-FIX-04)
  const approvedPresenters = state.presenters.filter(
    (p) => p.approvalStatus === 'APPROVED' && p.rightsStatus === 'VERIFIED',
  ).length
  const revokedPresenters = state.presenters.filter(
    (p) => p.rightsStatus === 'REVOKED',
  ).length
  const verifiedProducts = state.products.filter((p) => p.ocopStatus === 'VERIFIED').length
  const approvedKnowledge = state.knowledge.filter((k) => k.approvalStatus === 'APPROVED').length
  const liveSessions = state.sessions.filter((s) => s.lifecycle === 'LIVE').length

  return {
    ...base,
    featuredSession: syncedFeatured,
    recentSessions: syncedRecent,
    assetCards: [
      {
        id: 'presenter',
        label: 'AI Presenter',
        count: state.presenters.length,
        subtitle:
          revokedPresenters > 0
            ? `${revokedPresenters} thu hồi quyền · ${approvedPresenters} sẵn sàng`
            : `${approvedPresenters} sẵn sàng · ${state.presenters.length - approvedPresenters} đang xử lý`,
        statusLabel: revokedPresenters > 0 ? 'Cần xử lý quyền' : 'Đang quản lý',
        statusTone: revokedPresenters > 0 ? 'danger' : 'success',
        targetRoute: '/studio/presenters',
      },
      {
        id: 'products',
        label: 'Sản phẩm & OCOP',
        count: state.products.length,
        subtitle: `${verifiedProducts} đã xác minh · ${state.products.length - verifiedProducts} chờ OCOP`,
        statusLabel: `${verifiedProducts}/${state.products.length} đạt OCOP`,
        statusTone: verifiedProducts === state.products.length ? 'success' : 'info',
        targetRoute: '/studio/products',
      },
      {
        id: 'knowledge',
        label: 'Tri thức & Claims',
        count: approvedKnowledge,
        subtitle: `Gói SKU đã duyệt / ${state.knowledge.length} SKU`,
        statusLabel: 'Đã kiểm chứng',
        statusTone: 'success',
        targetRoute: '/studio/knowledge',
      },
      {
        id: 'sessions',
        label: 'Phiên đã tạo',
        count: state.sessions.length,
        subtitle: liveSessions > 0 ? `${liveSessions} đang livestream` : 'Chưa có phiên LIVE',
        statusLabel: liveSessions > 0 ? 'Đang vận hành' : 'Đang chuẩn bị',
        statusTone: liveSessions > 0 ? 'warning' : 'neutral',
        targetRoute: '/studio/sessions',
      },
    ],
  }
}
