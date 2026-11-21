import { delay, http, HttpResponse } from 'msw'
import type { UserRole } from '@/types/auth'
import type { MockScenarioKey } from '@/types/scenario'
import type {
  FactDecisionStatus,
  OnboardingDraft,
  PresenterDraftPayload,
  ProductDraftPayload,
  SessionDetail,
  StartCommandResult,
  StoryArcItem,
} from '@/types/m02'
import { buildAuthSnapshot } from '@/mocks/fixtures/workspace.fixtures'
import {
  buildSyncedDashboardSnapshot,
  computeReadiness,
  getStore,
  recomputeAllSessionReadiness,
  resetStore,
} from '@/mocks/store'
import { m03Handlers } from '@/mocks/m03.handlers'
import { resetM03Store } from '@/mocks/m03.store'

function readScenario(request: Request): MockScenarioKey {
  return (request.headers.get('X-Hostra-Scenario') as MockScenarioKey) || 'happy-path'
}

function readRole(request: Request): UserRole {
  const value = request.headers.get('X-Hostra-Role')?.toUpperCase()
  return value === 'OPERATOR' ? 'OPERATOR' : 'OWNER'
}

function forbiddenResponse(message: string) {
  return HttpResponse.json({ code: 'FORBIDDEN', message }, { status: 403 })
}

export const handlers = [
  /* ---------- Auth & Reset ---------- */
  http.get('/api/mock/v1/auth/me', async ({ request }) => {
    const scenario = readScenario(request)
    const role = readRole(request)
    await delay(60)
    return HttpResponse.json(
      buildAuthSnapshot(role, {
        emptyWorkspace: scenario === 'empty',
        unassignedOperator: scenario === 'permission-denied' && role === 'OPERATOR',
      }),
    )
  }),

  http.post('/api/mock/v1/reset', async ({ request }) => {
    const scenario = readScenario(request)
    resetStore(scenario)
    resetM03Store(scenario)
    return HttpResponse.json({ ok: true, scenario })
  }),

  /* ---------- Dashboard ---------- */
  http.get('/api/mock/v1/dashboard', async ({ request }) => {
    const scenario = readScenario(request)
    const role = readRole(request)

    if (scenario === 'loading') {
      await delay('infinite')
    }
    await delay(80)

    if (scenario === 'error') {
      return HttpResponse.json(
        {
          code: 'SNAPSHOT_UNAVAILABLE',
          message:
            'Không thể đồng bộ dữ liệu tổng quan từ máy chủ. Trạng thái hiện tại chưa được xác nhận.',
          requestId: 'req-mock-err-503',
        },
        { status: 503 },
      )
    }

    if (scenario === 'permission-denied') {
      return forbiddenResponse(
        'Tài khoản hiện tại không có quyền truy cập vào phạm vi dữ liệu này. Vui lòng liên hệ Chủ sở hữu workspace.',
      )
    }

    return HttpResponse.json(buildSyncedDashboardSnapshot(scenario, role))
  }),

  /* ---------- Onboarding ---------- */
  http.get('/api/mock/v1/onboarding', async ({ request }) => {
    const state = getStore(readScenario(request))
    await delay(50)
    return HttpResponse.json(state.onboarding)
  }),

  http.put('/api/mock/v1/onboarding', async ({ request }) => {
    const role = readRole(request)
    if (role !== 'OWNER') {
      return forbiddenResponse('Chỉ Chủ sở hữu mới được cập nhật thiết lập workspace.')
    }
    const state = getStore(readScenario(request))
    const body = (await request.json()) as Partial<OnboardingDraft>
    state.onboarding = {
      ...state.onboarding,
      ...body,
      savedAt: new Date().toISOString(),
      revision: state.onboarding.revision + 1,
    }
    return HttpResponse.json(state.onboarding)
  }),

  /* ---------- M02-A: Presenters & Rights Consent ---------- */
  http.get('/api/mock/v1/presenters', async ({ request }) => {
    const scenario = readScenario(request)
    if (scenario === 'loading') await delay('infinite')
    await delay(60)
    if (scenario === 'error') {
      return HttpResponse.json(
        { code: 'PRESENTER_LIST_ERROR', message: 'Không thể tải danh sách AI Presenter.' },
        { status: 503 },
      )
    }
    const state = getStore(scenario)
    return HttpResponse.json({ items: state.presenters })
  }),

  http.get('/api/mock/v1/presenters/:id', async ({ request, params }) => {
    await delay(60)
    const state = getStore(readScenario(request))
    const found = state.presenters.find((p) => p.id === params.id)
    if (!found) {
      return HttpResponse.json({ code: 'NOT_FOUND', message: 'Không tìm thấy AI Presenter.' }, { status: 404 })
    }
    return HttpResponse.json(found)
  }),

  http.post('/api/mock/v1/presenters', async ({ request }) => {
    const role = readRole(request)
    if (role !== 'OWNER') {
      return forbiddenResponse('Chỉ Chủ sở hữu mới có quyền tạo AI Presenter.')
    }
    const state = getStore(readScenario(request))
    const body = (await request.json()) as PresenterDraftPayload
    const id = `prs-custom-${state.presenters.length + 1}`
    const styleLabel =
      body.stylePreset === 'CHUYEN_NGHIEP'
        ? 'Chuyên nghiệp'
        : body.stylePreset === 'NANG_DONG'
          ? 'Năng động'
          : 'Thân thiện'

    const created = {
      id,
      workspaceId: 'ws-muong-lat-01',
      displayName: body.displayName.trim(),
      subjectName: body.subjectName.trim(),
      portraitNote: `Ảnh đã tải: ${body.portraitFileName || 'portrait_studio.jpg'} · Chờ xác nhận quyền`,
      stylePreset: body.stylePreset,
      styleLabel,
      voicePresetLabel: body.voicePresetLabel || 'Giọng nữ miền Bắc · Chuẩn cấp phép',
      rightsStatus: 'PENDING' as const,
      qcStatus: 'PENDING' as const,
      approvalStatus: 'NOT_REVIEWED' as const,
      generationState: 'NOT_STARTED' as const,
      activePackVersion: 'draft',
      updatedAt: new Date().toISOString(),
      rightsConsent: {
        requestId: `req-consent-${id}`,
        presenterId: id,
        subjectName: body.subjectName.trim(),
        purpose: 'Sử dụng hình ảnh tạo AI Presenter cho phòng livestream riêng tư HOSTRA',
        imageVideoScope: true,
        voiceCloneScope: false,
        status: 'PENDING' as const,
        rightsVersion: 1,
        expiresAt: '2027-06-30',
        updatedAt: new Date().toISOString(),
      },
      candidates: [],
      selectedCandidateId: null,
      approvedPackId: null,
      jobStageLabel: 'Đã lưu nháp · Chờ chủ thể xác nhận quyền',
      linkedSessionCodes: [],
    }
    state.presenters.unshift(created)
    recomputeAllSessionReadiness(state)
    return HttpResponse.json(created, { status: 201 })
  }),

  http.post('/api/mock/v1/presenters/:id/generate', async ({ request, params }) => {
    const role = readRole(request)
    if (role !== 'OWNER') {
      return forbiddenResponse('Chỉ Chủ sở hữu mới được gửi lệnh tạo clip.')
    }
    const state = getStore(readScenario(request))
    const item = state.presenters.find((p) => p.id === params.id)
    if (!item) return HttpResponse.json({ message: 'Không tìm thấy Presenter.' }, { status: 404 })
    if (item.rightsStatus !== 'VERIFIED') {
      return HttpResponse.json(
        {
          code: 'RIGHTS_NOT_VERIFIED',
          message: 'Không thể tạo clip khi quyền sử dụng hình ảnh chưa được Chủ thể quyền xác nhận hợp lệ.',
        },
        { status: 400 },
      )
    }

    const nextVer = item.candidates.length + 1
    const packId = `pack-${item.id}-v${nextVer}`
    item.generationState = 'COMPLETED'
    item.qcStatus = 'PASS'
    item.jobStageLabel = `Hoàn tất gói v${nextVer} · Đạt QC, chờ Chủ sở hữu duyệt`
    item.candidates.push({
      packId,
      versionLabel: `Gói v${nextVer} (Candidate mới)`,
      stylePreset: item.stylePreset,
      styleLabel: item.styleLabel,
      motionTemplate: 'Template M-04 · Giới thiệu đặc sản',
      generatedAt: new Date().toISOString(),
      qcStatus: 'PASS',
      rightsVersion: item.rightsConsent.rightsVersion,
      clips: [
        { id: `${packId}-c1`, label: 'Chào khách & mở đầu', role: 'INTRO', durationSec: 12, qcStatus: 'PASS' },
        { id: `${packId}-c2`, label: 'Giới thiệu sản phẩm', role: 'EXPLAIN', durationSec: 18, qcStatus: 'PASS' },
        { id: `${packId}-c3`, label: 'Chuyển cảnh tự nhiên', role: 'IDLE', durationSec: 8, qcStatus: 'PASS' },
      ],
    })
    item.selectedCandidateId = packId
    // Note: Newly generated version does NOT replace approved version automatically
    return HttpResponse.json(item)
  }),

  http.post('/api/mock/v1/presenters/:id/retry-clip', async ({ request, params }) => {
    const role = readRole(request)
    if (role !== 'OWNER') {
      return forbiddenResponse('Chỉ Chủ sở hữu mới được yêu cầu tạo lại clip.')
    }
    const state = getStore(readScenario(request))
    const item = state.presenters.find((p) => p.id === params.id)
    if (!item) return HttpResponse.json({ message: 'Không tìm thấy Presenter.' }, { status: 404 })
    if (item.rightsStatus !== 'VERIFIED') {
      return HttpResponse.json({ message: 'Quyền sử dụng không hợp lệ.' }, { status: 400 })
    }
    const nextVer = item.candidates.length + 1
    const packId = `pack-${item.id}-v${nextVer}`
    item.candidates.push({
      packId,
      versionLabel: `Gói v${nextVer} (Tạo lại clip lỗi · Đạt QC)`,
      stylePreset: item.stylePreset,
      styleLabel: item.styleLabel,
      motionTemplate: item.candidates[0]?.motionTemplate ?? 'Template M-02',
      generatedAt: new Date().toISOString(),
      qcStatus: 'PASS',
      rightsVersion: item.rightsConsent.rightsVersion,
      clips: [
        { id: `${packId}-c1`, label: 'Chào khách & mở đầu', role: 'INTRO', durationSec: 12, qcStatus: 'PASS' },
        { id: `${packId}-c2`, label: 'Giới thiệu thành phần (Tạo lại)', role: 'EXPLAIN', durationSec: 16, qcStatus: 'PASS' },
        { id: `${packId}-c3`, label: 'Chuyển cảnh tự nhiên', role: 'IDLE', durationSec: 8, qcStatus: 'PASS' },
      ],
    })
    item.selectedCandidateId = packId
    item.qcStatus = 'PASS'
    item.generationState = 'COMPLETED'
    item.jobStageLabel = 'Đã tạo lại clip lỗi · Toàn bộ gói đạt QC, chờ duyệt'
    return HttpResponse.json(item)
  }),

  http.post('/api/mock/v1/presenters/:id/approve', async ({ request, params }) => {
    const role = readRole(request)
    if (role !== 'OWNER') {
      return forbiddenResponse('Chỉ Chủ sở hữu mới có quyền phê duyệt AI Presenter.')
    }
    const state = getStore(readScenario(request))
    const item = state.presenters.find((p) => p.id === params.id)
    if (!item) return HttpResponse.json({ message: 'Không tìm thấy Presenter.' }, { status: 404 })
    const body = (await request.json()) as { packId: string; decision: 'APPROVE' | 'REWORK' }
    if (body.decision === 'REWORK') {
      item.approvalStatus = 'REWORK_REQUESTED'
      item.jobStageLabel = 'Đã yêu cầu chỉnh sửa lại gói clip'
      recomputeAllSessionReadiness(state)
      return HttpResponse.json(item)
    }
    const candidate = item.candidates.find((c) => c.packId === body.packId)
    if (!candidate || candidate.qcStatus !== 'PASS' || item.rightsStatus !== 'VERIFIED') {
      return HttpResponse.json(
        { message: 'Chỉ được phê duyệt khi gói clip đạt QC và quyền sử dụng đang hợp lệ.' },
        { status: 400 },
      )
    }
    item.approvedPackId = candidate.packId
    item.selectedCandidateId = candidate.packId
    item.approvalStatus = 'APPROVED'
    item.qcStatus = 'PASS'
    item.activePackVersion = `v${item.candidates.indexOf(candidate) + 1}`
    item.jobStageLabel = `Đã phê duyệt ${candidate.versionLabel}`
    recomputeAllSessionReadiness(state)
    return HttpResponse.json(item)
  }),

  http.get('/api/mock/v1/rights/:requestId', async ({ request, params }) => {
    await delay(50)
    const state = getStore(readScenario(request))
    const presenter = state.presenters.find((p) => p.rightsConsent.requestId === params.requestId)
    if (!presenter) {
      return HttpResponse.json({ message: 'Không tìm thấy yêu cầu xác nhận quyền.' }, { status: 404 })
    }
    return HttpResponse.json({
      presenterName: presenter.displayName,
      consent: presenter.rightsConsent,
    })
  }),

  http.post('/api/mock/v1/rights/:requestId/decision', async ({ request, params }) => {
    const state = getStore(readScenario(request))
    const presenter = state.presenters.find((p) => p.rightsConsent.requestId === params.requestId)
    if (!presenter) {
      return HttpResponse.json({ message: 'Không tìm thấy yêu cầu xác nhận quyền.' }, { status: 404 })
    }
    const body = (await request.json()) as { action: 'ACCEPT' | 'DECLINE' | 'REVOKE' }
    const nextStatus =
      body.action === 'ACCEPT'
        ? 'VERIFIED'
        : body.action === 'DECLINE'
          ? 'DECLINED'
          : 'REVOKED'
    presenter.rightsConsent.status = nextStatus
    presenter.rightsConsent.rightsVersion += 1
    presenter.rightsConsent.updatedAt = new Date().toISOString()
    presenter.rightsStatus = nextStatus
    if (nextStatus === 'REVOKED' || nextStatus === 'DECLINED') {
      presenter.jobStageLabel = 'Bị khóa do Chủ thể quyền từ chối/thu hồi'
    } else {
      presenter.jobStageLabel = 'Quyền hợp lệ · Sẵn sàng tạo clip'
    }
    recomputeAllSessionReadiness(state)
    return HttpResponse.json({ presenterName: presenter.displayName, consent: presenter.rightsConsent })
  }),

  /* ---------- M02-B: Products & OCOP ---------- */
  http.get('/api/mock/v1/products', async ({ request }) => {
    const scenario = readScenario(request)
    if (scenario === 'loading') await delay('infinite')
    await delay(60)
    const state = getStore(scenario)
    return HttpResponse.json({ items: state.products })
  }),

  http.get('/api/mock/v1/products/:skuId', async ({ request, params }) => {
    await delay(60)
    const state = getStore(readScenario(request))
    const product = state.products.find((p) => p.skuId === params.skuId)
    if (!product) {
      return HttpResponse.json({ message: 'Không tìm thấy sản phẩm.' }, { status: 404 })
    }
    return HttpResponse.json(product)
  }),

  http.post('/api/mock/v1/products', async ({ request }) => {
    const role = readRole(request)
    const state = getStore(readScenario(request))
    const body = (await request.json()) as ProductDraftPayload & { submitForVerification?: boolean }
    if (body.submitForVerification && role !== 'OWNER') {
      return forbiddenResponse('Chỉ Chủ sở hữu mới có quyền Gửi xác minh OCOP (PC-D5).')
    }
    const skuId = `sku-custom-${state.products.length + 1}`
    const created = {
      skuId,
      skuCode: body.skuCode.trim().toUpperCase(),
      workspaceId: 'ws-muong-lat-01',
      name: body.name.trim(),
      category: body.category || 'Thực phẩm đóng gói',
      priceVnd: Number(body.priceVnd) || 0,
      packSpec: body.packSpec || 'Đóng gói tiêu chuẩn',
      origin: body.origin || 'Thanh Hóa',
      expiryLabel: body.expiryLabel || '12 tháng',
      description: body.description || '',
      brandName: 'Đặc sản Mường Lát',
      ocopStatus: 'PENDING_REVIEW' as const,
      ocopDecisionCode: body.ocopDecisionCode || undefined,
      ocopReasonNote: body.submitForVerification
        ? 'Đã gửi hồ sơ sang P09 chờ xác minh độc lập (không tự động VERIFIED).'
        : 'Bản nháp đã lưu — chưa gửi xác minh OCOP.',
      knowledgeStatus: 'DRAFT' as const,
      sessionEligible: false,
      submittedByOwner: Boolean(body.submitForVerification),
      evidenceFiles: [],
      missingChecklist: [
        { id: 'mc-1', label: 'Chủ thể đăng ký khớp doanh nghiệp/HTX', required: true, satisfied: true },
        { id: 'mc-2', label: 'Quyết định công nhận OCOP còn hiệu lực', required: true, satisfied: Boolean(body.ocopDecisionCode) },
        { id: 'mc-3', label: 'Nhãn thực phẩm đóng gói & hạn sử dụng', required: true, satisfied: Boolean(body.packSpec) },
      ],
      versions: [
        {
          version: 1,
          updatedAt: new Date().toISOString(),
          actorName: role === 'OWNER' ? 'Nguyễn Minh Quân' : 'Trần Ngọc Lan',
          summary: body.submitForVerification
            ? 'Tạo hồ sơ và gửi xác minh OCOP'
            : 'Lưu bản nháp sản phẩm mới',
        },
      ],
      linkedSessionCodes: [],
      updatedAt: new Date().toISOString(),
      revision: 1,
    }
    state.products.unshift(created)
    state.knowledge.unshift({
      skuId,
      skuCode: created.skuCode,
      productName: created.name,
      ocopStatus: 'PENDING_REVIEW',
      approvalStatus: 'DRAFT',
      extractionStatus: 'COMPLETED',
      activeVersion: 0,
      draftRevision: 1,
      sourceDocTitle: `Ho_so_${created.skuCode}.pdf`,
      sourceDocVersion: 'v0.1',
      sourceDocPassages: [
        { page: 'Trang 1', heading: 'Thông tin sản phẩm', text: `${created.name} · Giá ${created.priceVnd} đ · ${created.packSpec} · Xuất xứ ${created.origin}.` },
      ],
      items: [
        {
          id: `kf-${skuId}-1`,
          group: 'PRICE',
          label: 'Giá bán đề xuất',
          proposedValue: `${created.priceVnd.toLocaleString('vi-VN')} đ`,
          sourceFile: `Ho_so_${created.skuCode}.pdf`,
          sourcePage: 'Trang 1',
          sourceExcerpt: `Giá ${created.priceVnd} đ.`,
          decision: 'REVIEW_REQUIRED',
          required: true,
        },
      ],
      speechPreviewLines: [],
      versions: [],
      updatedAt: new Date().toISOString(),
    })
    recomputeAllSessionReadiness(state)
    return HttpResponse.json(created, { status: 201 })
  }),

  http.post('/api/mock/v1/products/:skuId/evidence', async ({ request, params }) => {
    const role = readRole(request)
    const state = getStore(readScenario(request))
    const product = state.products.find((p) => p.skuId === params.skuId)
    if (!product) return HttpResponse.json({ message: 'Không tìm thấy sản phẩm.' }, { status: 404 })
    const body = (await request.json()) as { fileName: string; documentType: 'OCOP_CERT' | 'FOOD_SAFETY' | 'PRODUCT_LABEL' | 'ORIGIN_DOC' }
    const typeLabelMap = {
      OCOP_CERT: 'Quyết định công nhận OCOP',
      FOOD_SAFETY: 'Chứng nhận an toàn thực phẩm',
      PRODUCT_LABEL: 'Nhãn bao bì sản phẩm',
      ORIGIN_DOC: 'Chứng từ nguồn gốc / phân phối',
    }
    product.evidenceFiles.push({
      id: `ev-${Date.now()}`,
      fileName: body.fileName,
      documentType: body.documentType,
      documentTypeLabel: typeLabelMap[body.documentType],
      uploadedBy: role === 'OWNER' ? 'Nguyễn Minh Quân' : 'Trần Ngọc Lan',
      uploadedAt: new Date().toISOString(),
      sizeKb: 312,
      provenanceNote: 'Tài liệu mới tải lên (chưa tự động xác minh OCOP)',
    })
    if (body.documentType === 'OCOP_CERT') {
      const item = product.missingChecklist.find((m) => m.id === 'mc-2')
      if (item) item.satisfied = true
    } else {
      const item = product.missingChecklist.find((m) => m.id === 'mc-3')
      if (item) item.satisfied = true
    }
    product.revision += 1
    product.updatedAt = new Date().toISOString()
    return HttpResponse.json(product)
  }),

  http.post('/api/mock/v1/products/:skuId/submit-ocop', async ({ request, params }) => {
    const role = readRole(request)
    if (role !== 'OWNER') {
      return forbiddenResponse('Chỉ Chủ sở hữu mới được gửi hồ sơ xác minh OCOP.')
    }
    const state = getStore(readScenario(request))
    const product = state.products.find((p) => p.skuId === params.skuId)
    if (!product) return HttpResponse.json({ message: 'Không tìm thấy sản phẩm.' }, { status: 404 })
    product.submittedByOwner = true
    product.ocopStatus = 'PENDING_REVIEW'
    product.ocopReasonNote = 'Chủ sở hữu đã gửi hồ sơ xác minh. Đang chờ cơ quan / Reviewer P09 đối chiếu độc lập.'
    product.versions.unshift({
      version: product.versions.length + 1,
      updatedAt: new Date().toISOString(),
      actorName: 'Nguyễn Minh Quân',
      summary: 'Gửi hồ sơ đề nghị xác minh OCOP độc lập',
    })
    return HttpResponse.json(product)
  }),

  // Mock Reviewer verdict endpoint (clearly separate from Merchant role — simulates P09 authority)
  http.post('/api/mock/v1/products/:skuId/mock-reviewer-verdict', async ({ request, params }) => {
    const state = getStore(readScenario(request))
    const product = state.products.find((p) => p.skuId === params.skuId)
    if (!product) return HttpResponse.json({ message: 'Không tìm thấy sản phẩm.' }, { status: 404 })
    const body = (await request.json()) as { verdict: 'VERIFIED' | 'PENDING_REVIEW' | 'REJECTED' | 'REVOKED' }
    product.ocopStatus = body.verdict
    product.ocopCheckedAt = new Date().toISOString()
    if (body.verdict === 'VERIFIED') {
      product.ocopStars = product.ocopStars ?? 3
      product.ocopAuthoritySource = 'P09 Reviewer (Mô phỏng) · Đối chiếu cổng OCOP'
      product.ocopReasonNote = 'Hồ sơ khớp nguồn xác minh OCOP độc lập (kết quả mô phỏng).'
      product.sessionEligible = product.knowledgeStatus === 'APPROVED'
    } else if (body.verdict === 'REJECTED') {
      product.ocopReasonNote = 'Chứng từ chưa khớp thông tin chủ thể hoặc đã hết thời hạn công nhận.'
      product.sessionEligible = false
    } else if (body.verdict === 'REVOKED') {
      product.ocopReasonNote = 'Chứng nhận OCOP bị thu hồi — khóa sử dụng trong mọi phiên livestream.'
      product.sessionEligible = false
    } else {
      product.ocopReasonNote = 'Chưa đủ căn cứ xác minh — chờ bổ sung tài liệu.'
      product.sessionEligible = false
    }
    const kg = state.knowledge.find((k) => k.skuId === product.skuId)
    if (kg) kg.ocopStatus = body.verdict
    recomputeAllSessionReadiness(state)
    return HttpResponse.json(product)
  }),

  /* ---------- M02-C: Knowledge & Claims ---------- */
  http.get('/api/mock/v1/knowledge', async ({ request }) => {
    await delay(60)
    const state = getStore(readScenario(request))
    return HttpResponse.json({ items: state.knowledge })
  }),

  http.get('/api/mock/v1/knowledge/:skuId', async ({ request, params }) => {
    await delay(60)
    const state = getStore(readScenario(request))
    const pkg = state.knowledge.find((k) => k.skuId === params.skuId)
    if (!pkg) return HttpResponse.json({ message: 'Không tìm thấy hồ sơ tri thức.' }, { status: 404 })
    return HttpResponse.json(pkg)
  }),

  http.post('/api/mock/v1/knowledge/:skuId/items/:itemId/decision', async ({ request, params }) => {
    const role = readRole(request)
    const state = getStore(readScenario(request))
    const pkg = state.knowledge.find((k) => k.skuId === params.skuId)
    if (!pkg) return HttpResponse.json({ message: 'Không tìm thấy gói tri thức.' }, { status: 404 })
    const item = pkg.items.find((i) => i.id === params.itemId)
    if (!item) return HttpResponse.json({ message: 'Không tìm thấy mục tri thức.' }, { status: 404 })
    if (item.decision === 'BLOCKED') {
      return HttpResponse.json(
        { message: 'Claim bị chặn bởi chính sách an toàn không thể được phê duyệt.' },
        { status: 400 },
      )
    }
    const body = (await request.json()) as { decision: FactDecisionStatus; proposedValue?: string }
    if (body.decision === 'APPROVED' && role !== 'OWNER') {
      return forbiddenResponse('Chỉ Chủ sở hữu mới có quyền phê duyệt mục tri thức (KC-D4).')
    }
    item.decision = body.decision
    if (typeof body.proposedValue === 'string' && body.proposedValue.trim()) {
      item.proposedValue = body.proposedValue.trim()
    }
    pkg.draftRevision += 1
    if (pkg.approvalStatus === 'APPROVED') {
      pkg.approvalStatus = 'PENDING_OWNER'
      const prod = state.products.find((p) => p.skuId === pkg.skuId)
      if (prod) prod.knowledgeStatus = 'PENDING_OWNER'
    }
    recomputeAllSessionReadiness(state)
    return HttpResponse.json(pkg)
  }),

  http.post('/api/mock/v1/knowledge/:skuId/approve-bundle', async ({ request, params }) => {
    const role = readRole(request)
    if (role !== 'OWNER') {
      return forbiddenResponse('Chỉ Chủ sở hữu mới có quyền phê duyệt gói tri thức.')
    }
    const state = getStore(readScenario(request))
    const pkg = state.knowledge.find((k) => k.skuId === params.skuId)
    if (!pkg) return HttpResponse.json({ message: 'Không tìm thấy gói tri thức.' }, { status: 404 })
    const unreviewedRequired = pkg.items.filter(
      (i) => i.required && i.decision !== 'APPROVED',
    )
    if (unreviewedRequired.length > 0) {
      return HttpResponse.json(
        {
          message: `Còn ${unreviewedRequired.length} mục bắt buộc chưa được duyệt. Không hỗ trợ duyệt mù cả tài liệu (KC-D3).`,
        },
        { status: 400 },
      )
    }
    pkg.activeVersion += 1
    pkg.approvalStatus = 'APPROVED'
    pkg.updatedAt = new Date().toISOString()
    pkg.speechPreviewLines = pkg.items
      .filter((i) => i.decision === 'APPROVED')
      .map((i) => ({
        text: `${i.label}: ${i.proposedValue}.`,
        sourceRef: `${i.sourceFile} · ${i.sourcePage}`,
      }))
    pkg.versions.unshift({
      version: pkg.activeVersion,
      status: 'APPROVED',
      approvedBy: 'Nguyễn Minh Quân',
      approvedAt: pkg.updatedAt,
      summary: `Phê duyệt gói tri thức v${pkg.activeVersion} (đã loại bỏ các mục bị chặn)`,
    })
    const prod = state.products.find((p) => p.skuId === pkg.skuId)
    if (prod) {
      prod.knowledgeStatus = 'APPROVED'
      prod.sessionEligible = prod.ocopStatus === 'VERIFIED'
    }
    recomputeAllSessionReadiness(state)
    return HttpResponse.json(pkg)
  }),

  /* ---------- M02-D: Story Planner ---------- */
  http.get('/api/mock/v1/sessions/:id/story', async ({ request, params }) => {
    await delay(60)
    const state = getStore(readScenario(request))
    const plan = state.storyPlans[String(params.id)]
    if (!plan) {
      return HttpResponse.json({ message: 'Không tìm thấy kịch bản của phiên này.' }, { status: 404 })
    }
    return HttpResponse.json(plan)
  }),

  http.put('/api/mock/v1/sessions/:id/story', async ({ request, params }) => {
    const role = readRole(request)
    if (role !== 'OWNER') {
      return forbiddenResponse(
        'Quyền sửa kịch bản trước phiên của Vận hành viên hiện đang mở (OPEN) — mặc định chỉ Chủ sở hữu được thao tác.',
      )
    }
    const state = getStore(readScenario(request))
    const plan = state.storyPlans[String(params.id)]
    if (!plan) return HttpResponse.json({ message: 'Không tìm thấy kịch bản.' }, { status: 404 })
    const body = (await request.json()) as { arcs: StoryArcItem[]; summary?: string }
    plan.arcs = body.arcs.map((a, idx) => ({ ...a, position: idx + 1 }))
    plan.planRevision += 1
    plan.approvalStatus = 'REVIEW_REQUIRED'
    plan.dirtyReason = 'Kịch bản vừa được chỉnh sửa — cần Chủ sở hữu rà soát từng đoạn và duyệt lại phiên bản mới.'
    plan.revisionHistory.unshift({
      revision: plan.planRevision,
      actor: 'Nguyễn Minh Quân',
      summary: body.summary || 'Cập nhật thứ tự/nội dung kịch bản nháp',
      timestamp: new Date().toISOString(),
    })
    recomputeAllSessionReadiness(state)
    return HttpResponse.json(plan)
  }),

  http.post('/api/mock/v1/sessions/:id/story/ai-suggest', async ({ request, params }) => {
    await delay(220)
    const state = getStore(readScenario(request))
    const plan = state.storyPlans[String(params.id)]
    if (!plan) return HttpResponse.json({ message: 'Không tìm thấy kịch bản.' }, { status: 404 })
    const body = (await request.json()) as { prompt: string }
    const prompt = body.prompt.trim()
    const lower = prompt.toLowerCase()
    const hasMedicalClaim =
      lower.includes('chữa bệnh') ||
      lower.includes('đau dạ dày') ||
      lower.includes('tiểu đường') ||
      lower.includes('ung thư')

    const cloned = plan.arcs.map((a) => ({ ...a }))
    const summary = 'Đề xuất rút gọn phần mở đầu và ưu tiên giới thiệu nguồn gốc trước khi nêu cách bảo quản.'
    if (cloned.length >= 3) {
      cloned[0].durationMin = Math.max(2, cloned[0].durationMin - 1)
      cloned[1].title = 'Nguồn gốc đặc sản Mường Lát (Ưu tiên)'
      cloned[1].previewText =
        'Mứt Mận Mường Lát được chế biến từ 85% mận hậu vùng cao Thanh Hóa, đạt chuẩn OCOP 4 sao, sau đó hướng dẫn bảo quản nơi khô mát.'
    }

    plan.lastProposal = {
      proposalId: `prop-${Date.now()}`,
      prompt,
      summary,
      unsupportedWarning: hasMedicalClaim
        ? 'Cảnh báo an toàn: Yêu cầu chứa tuyên bố công dụng y tế/chữa bệnh không có bằng chứng hợp lệ nên đã bị loại khỏi bản đề xuất.'
        : undefined,
      beforeSummary: plan.arcs.map((a) => `${a.position}. ${a.title} (${a.durationMin}p)`).join(' → '),
      afterSummary: cloned.map((a) => `${a.position}. ${a.title} (${a.durationMin}p)`).join(' → '),
      proposedArcs: cloned,
      status: 'PROPOSAL_READY',
    }
    return HttpResponse.json(plan)
  }),

  http.post('/api/mock/v1/sessions/:id/story/ai-apply', async ({ request, params }) => {
    const role = readRole(request)
    if (role !== 'OWNER') {
      return forbiddenResponse('Chỉ Chủ sở hữu mới được áp dụng đề xuất vào bản nháp pre-live.')
    }
    const state = getStore(readScenario(request))
    const plan = state.storyPlans[String(params.id)]
    if (!plan || !plan.lastProposal) {
      return HttpResponse.json({ message: 'Không có đề xuất AI nào để áp dụng.' }, { status: 400 })
    }
    const body = (await request.json()) as { action: 'APPLY' | 'REJECT' }
    if (body.action === 'REJECT') {
      plan.lastProposal.status = 'REJECTED'
      return HttpResponse.json(plan)
    }
    plan.arcs = plan.lastProposal.proposedArcs.map((a, idx) => ({
      ...a,
      position: idx + 1,
      reviewed: false,
    }))
    plan.lastProposal.status = 'APPLIED'
    plan.planRevision += 1
    plan.approvalStatus = 'REVIEW_REQUIRED'
    plan.dirtyReason = 'Đã áp dụng đề xuất từ Trợ lý AI vào bản nháp — cần Chủ sở hữu duyệt lại toàn bộ phiên bản.'
    plan.revisionHistory.unshift({
      revision: plan.planRevision,
      actor: 'Nguyễn Minh Quân',
      summary: `Áp dụng đề xuất AI: “${plan.lastProposal.prompt}”`,
      timestamp: new Date().toISOString(),
    })
    recomputeAllSessionReadiness(state)
    return HttpResponse.json(plan)
  }),

  http.post('/api/mock/v1/sessions/:id/story/approve', async ({ request, params }) => {
    const role = readRole(request)
    if (role !== 'OWNER') {
      return forbiddenResponse('Chỉ Chủ sở hữu mới được phê duyệt phiên bản Story Plan (SS-D4).')
    }
    const state = getStore(readScenario(request))
    const plan = state.storyPlans[String(params.id)]
    if (!plan) return HttpResponse.json({ message: 'Không tìm thấy kịch bản.' }, { status: 404 })
    const unreviewed = plan.arcs.filter((a) => !a.reviewed)
    if (unreviewed.length > 0) {
      return HttpResponse.json(
        { message: `Còn ${unreviewed.length} đoạn kịch bản chưa được đánh dấu đã rà soát.` },
        { status: 400 },
      )
    }
    plan.approvalStatus = 'APPROVED'
    plan.approvedRevision = plan.planRevision
    plan.approvedBy = 'Nguyễn Minh Quân'
    plan.approvedAt = new Date().toISOString()
    plan.dirtyReason = undefined
    recomputeAllSessionReadiness(state)
    return HttpResponse.json(plan)
  }),

  /* ---------- M02-E & F: Sessions & Readiness ---------- */
  http.get('/api/mock/v1/sessions', async ({ request }) => {
    await delay(60)
    const role = readRole(request)
    const state = getStore(readScenario(request))
    const items =
      role === 'OWNER'
        ? state.sessions
        : state.sessions.filter((s) => s.assignedOperatorIds.includes('usr-op-01'))
    return HttpResponse.json({ items })
  }),

  http.get('/api/mock/v1/sessions/:id', async ({ request, params }) => {
    await delay(60)
    const state = getStore(readScenario(request))
    const session = state.sessions.find((s) => s.id === params.id)
    if (!session) return HttpResponse.json({ message: 'Không tìm thấy phiên.' }, { status: 404 })
    return HttpResponse.json(session)
  }),

  http.post('/api/mock/v1/sessions', async ({ request }) => {
    const role = readRole(request)
    if (role !== 'OWNER') {
      return forbiddenResponse('Chỉ Chủ sở hữu mới có quyền tạo phiên livestream mới.')
    }
    const state = getStore(readScenario(request))
    const body = (await request.json()) as {
      title: string
      presenterId: string
      selectedSkuIds: string[]
      goal: string
      theme: string
      estimatedMinutes: number
      prioritySkuId: string | null
      mandatoryMessages: string
    }
    const uniqueSkus = Array.from(new Set(body.selectedSkuIds))
    if (uniqueSkus.length > 5) {
      return HttpResponse.json({ message: 'Mỗi phiên chỉ được chọn tối đa 5 SKU.' }, { status: 400 })
    }
    const presenter = state.presenters.find((p) => p.id === body.presenterId)
    const nextNum = 16 + state.sessions.filter((s) => s.id.startsWith('ses-new')).length
    const id = `ses-new-${nextNum}`
    const code = `Phiên #0${nextNum}`
    const created: SessionDetail = {
      id,
      code,
      workspaceId: 'ws-muong-lat-01',
      title: body.title.trim() || `Phiên giới thiệu đặc sản #0${nextNum}`,
      lifecycle: 'PREPARING',
      aiState: 'PAUSED',
      mediaHealth: 'HEALTHY',
      presenterId: body.presenterId,
      presenterName: presenter?.displayName ?? 'Chưa chọn Presenter',
      skuCount: uniqueSkus.length,
      assignedOperatorIds: ['usr-op-01'],
      updatedAt: new Date().toISOString(),
      revision: 1,
      epoch: 1,
      goal: body.goal,
      theme: body.theme,
      estimatedMinutes: body.estimatedMinutes || 30,
      prioritySkuId: body.prioritySkuId,
      mandatoryMessages: body.mandatoryMessages,
      selectedSkuIds: uniqueSkus,
      selectedPresenterVersion: presenter?.activePackVersion ?? 'draft',
      storyApprovalStatus: 'DRAFT',
      readinessOverall: 'BLOCKED',
      readinessBlockedCount: 1,
    }
    state.sessions.unshift(created)
    state.storyPlans[id] = {
      sessionId: id,
      sessionCode: code,
      sessionTitle: created.title,
      planRevision: 1,
      approvedRevision: null,
      approvalStatus: 'DRAFT',
      dirtyReason: 'Kịch bản mới khởi tạo — cần Chủ sở hữu rà soát và phê duyệt.',
      arcs: uniqueSkus.map((skuId, index) => {
        const prod = state.products.find((p) => p.skuId === skuId)
        return {
          id: `arc-${id}-${index + 1}`,
          position: index + 1,
          title: prod ? `Giới thiệu ${prod.name}` : `Đoạn ${index + 1}`,
          durationMin: 6,
          skuId,
          skuLabel: prod ? `${prod.skuCode} · ${prod.name}` : skuId,
          topic: 'Giới thiệu thông tin, nguồn gốc và giá niêm yết đã duyệt',
          previewText: prod
            ? `${prod.name} (${prod.packSpec}), giá ${prod.priceVnd.toLocaleString('vi-VN')} đ.`
            : 'Nội dung dự kiến theo tri thức đã duyệt.',
          factRefs: prod ? [`Hồ sơ ${prod.skuCode}`] : [],
          reviewed: false,
        }
      }),
      lastProposal: null,
      revisionHistory: [
        { revision: 1, actor: 'Nguyễn Minh Quân', summary: 'Khởi tạo kịch bản từ Session Wizard', timestamp: new Date().toISOString() },
      ],
    }
    recomputeAllSessionReadiness(state)
    return HttpResponse.json(created, { status: 201 })
  }),

  http.put('/api/mock/v1/sessions/:id', async ({ request, params }) => {
    const role = readRole(request)
    if (role !== 'OWNER') {
      return forbiddenResponse('Chỉ Chủ sở hữu mới được chỉnh sửa cấu hình phiên trước khi phát.')
    }
    const state = getStore(readScenario(request))
    const session = state.sessions.find((s) => s.id === params.id)
    if (!session) return HttpResponse.json({ message: 'Không tìm thấy phiên.' }, { status: 404 })
    const body = (await request.json()) as Partial<SessionDetail>
    if (body.selectedSkuIds) {
      const unique = Array.from(new Set(body.selectedSkuIds))
      if (unique.length > 5) {
        return HttpResponse.json({ message: 'Tối đa 5 SKU mỗi phiên.' }, { status: 400 })
      }
      const changed = JSON.stringify(unique) !== JSON.stringify(session.selectedSkuIds)
      session.selectedSkuIds = unique
      session.skuCount = unique.length
      if (changed && state.storyPlans[session.id]) {
        state.storyPlans[session.id].approvalStatus = 'INVALIDATED'
        state.storyPlans[session.id].dirtyReason =
          'Danh sách/thứ tự SKU vừa thay đổi — cần rà soát và duyệt lại Story Plan.'
      }
    }
    if (body.title) session.title = body.title
    if (body.goal !== undefined) session.goal = body.goal
    if (body.theme !== undefined) session.theme = body.theme
    if (body.presenterId) {
      session.presenterId = body.presenterId
      const p = state.presenters.find((x) => x.id === body.presenterId)
      if (p) {
        session.presenterName = p.displayName
        session.selectedPresenterVersion = p.activePackVersion
      }
    }
    session.revision += 1
    session.updatedAt = new Date().toISOString()
    recomputeAllSessionReadiness(state)
    return HttpResponse.json(session)
  }),

  http.get('/api/mock/v1/sessions/:id/readiness', async ({ request, params }) => {
    await delay(80)
    const state = getStore(readScenario(request))
    recomputeAllSessionReadiness(state)
    const snap = computeReadiness(state, String(params.id))
    if (!snap) return HttpResponse.json({ message: 'Không tìm thấy phiên.' }, { status: 404 })
    return HttpResponse.json(snap)
  }),

  http.post('/api/mock/v1/sessions/:id/start', async ({ request, params }) => {
    const role = readRole(request)
    if (role !== 'OWNER') {
      return forbiddenResponse('Chỉ Chủ sở hữu mới có quyền khởi chạy livestream (START).')
    }
    await delay(150)
    const state = getStore(readScenario(request))
    const session = state.sessions.find((s) => s.id === params.id)
    if (!session) return HttpResponse.json({ message: 'Không tìm thấy phiên.' }, { status: 404 })
    const snap = computeReadiness(state, session.id)
    const body = (await request.json()) as { phase?: 'REQUEST' | 'CONFIRM_MEDIA' }

    if (!snap?.overallReady) {
      const rejected: StartCommandResult = {
        commandId: `cmd-start-${Date.now()}`,
        status: 'REJECTED',
        lifecycle: session.lifecycle,
        reason: 'Chưa thể khởi chạy: còn điều kiện Readiness đang bị chặn hoặc chờ xác minh.',
        isMockRuntime: true,
      }
      return HttpResponse.json(rejected, { status: 409 })
    }

    if (body.phase === 'CONFIRM_MEDIA') {
      session.lifecycle = 'LIVE'
      session.aiState = 'ACTIVE'
      session.mediaHealth = 'HEALTHY'
      session.startedAt = new Date().toISOString()
      session.revision += 1
      const applied: StartCommandResult = {
        commandId: `cmd-start-${Date.now()}`,
        status: 'APPLIED',
        lifecycle: 'LIVE',
        reason: 'Hệ thống phát mô phỏng đã xác nhận — phiên chuyển sang LIVE (Mock Runtime).',
        isMockRuntime: true,
      }
      return HttpResponse.json(applied)
    }

    session.lifecycle = 'STARTING'
    session.revision += 1
    const accepted: StartCommandResult = {
      commandId: `cmd-start-${Date.now()}`,
      status: 'ACCEPTED',
      lifecycle: 'STARTING',
      reason: 'Backend đã tiếp nhận lệnh START (ACCEPTED). Đang chờ xác nhận media/publisher trước khi LIVE.',
      isMockRuntime: true,
    }
    return HttpResponse.json(accepted)
  }),

  ...m03Handlers,
]
