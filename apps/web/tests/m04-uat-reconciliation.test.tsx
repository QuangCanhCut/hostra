import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { ThemeProvider } from '@/hooks/useTheme'
import { ScenarioProvider } from '@/hooks/useScenario'
import { AppShell } from '@/app/layouts/AppShell'
import { ReportsHistoryPage } from '@/features/reports/pages/ReportsHistoryPage'
import { SessionReportPage } from '@/features/reports/pages/SessionReportPage'
import { getStore, computeReadiness, recomputeAllSessionReadiness } from '@/mocks/store'
import {
  advanceSpeechTurnPhase,
  buildControlRoomSnapshot,
  buildSessionReport,
  buildViewerRoomSnapshot,
  getM03Store,
  isActorAssignedToSession,
} from '@/mocks/m03.store'
import { formatClockTime } from '@/lib/format'
import { buildSanitizedAuditCsv, buildSummaryPdfBlob, sanitizeCsvCell } from '@/lib/export-utils'

function renderReports(initialUrl: string) {
  window.history.pushState({}, '', initialUrl)
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ScenarioProvider>
          <MemoryRouter initialEntries={[initialUrl]}>
            <Routes>
              <Route path="/studio" element={<AppShell />}>
                <Route path="reports" element={<ReportsHistoryPage />} />
                <Route path="sessions/:id/report" element={<SessionReportPage />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </ScenarioProvider>
      </ThemeProvider>
    </QueryClientProvider>,
  )
}

describe('Milestone 04 — Gate 1 Reconciliation & Gate 2 Cross-Module UAT Invariants', () => {
  it('Gate 1 (3.2 & 3.3): Session #013 timestamps, duration, and admissions chart reconcile 100% with canonical store', () => {
    const core = getStore('happy-path')
    const ses013 = core.sessions.find((s) => s.id === 'ses-013')!
    const reportOwner = buildSessionReport('happy-path', 'OWNER', 'ses-013')!
    const reportOp = buildSessionReport('happy-path', 'OPERATOR', 'ses-013')!

    // Start & End match canonical session exactly
    expect(reportOwner.startedAt).toBe(ses013.startedAt)
    expect(reportOwner.stoppedAt).toBe(ses013.stoppedAt)
    expect(reportOwner.startedAt).toBe('2026-11-19T12:00:00Z')
    expect(reportOwner.stoppedAt).toBe('2026-11-19T13:32:00Z')

    // Presentation timezone (Asia/Ho_Chi_Minh) is deterministic regardless of role
    expect(formatClockTime(reportOwner.startedAt!)).toBe('19:00')
    expect(formatClockTime(reportOwner.stoppedAt!)).toBe('20:32')
    expect(reportOwner.timeline[0].timeLabel).toBe('19:00')
    expect(reportOp.timeline[0].timeLabel).toBe('19:00')

    // Every timeline event falls inside [startedAt, stoppedAt]
    const startMs = new Date(ses013.startedAt!).getTime()
    const endMs = new Date(ses013.stoppedAt!).getTime()
    for (const seg of reportOwner.timeline) {
      const t = new Date(seg.occurredAtIso).getTime()
      expect(t).toBeGreaterThanOrEqual(startMs)
      expect(t).toBeLessThanOrEqual(endMs)
    }

    // Chart admissions sum === KPI Successful Admissions (86 === 86)
    const admissionsKpi = reportOwner.kpis.find((k) => k.key === 'guest_successful_admissions')!
    const chartSum = reportOwner.intervalChart.reduce((sum, pt) => sum + pt.admissions, 0)
    expect(admissionsKpi.value).toBe(86)
    expect(chartSum).toBe(86)

    // Concurrent viewers is NOT inferred from admissions when telemetry is missing
    const concurrentKpi = reportOwner.kpis.find((k) => k.key === 'concurrent_viewers')!
    expect(concurrentKpi.value).toBeNull()
    expect(concurrentKpi.status).toBe('NOT_AVAILABLE')
    expect(reportOwner.reportStatus).toBe('PARTIAL')
    expect(reportOwner.canExport).toBe(false)
  })

  it('Gate 1 (3.4): Export availability messaging accurately reflects PENDING, PARTIAL, READY, and Operator role', async () => {
    const rep015 = buildSessionReport('happy-path', 'OWNER', 'ses-015')!
    expect(rep015.reportStatus).toBe('PENDING')
    expect(rep015.canExport).toBe(false)
    expect(rep015.intervalChart).toHaveLength(0)

    const rep012Owner = buildSessionReport('happy-path', 'OWNER', 'ses-012')!
    expect(rep012Owner.reportStatus).toBe('READY')
    expect(rep012Owner.canExport).toBe(true)
    const chartSum012 = rep012Owner.intervalChart.reduce((s, p) => s + p.admissions, 0)
    expect(chartSum012).toBe(
      rep012Owner.kpis.find((k) => k.key === 'guest_successful_admissions')?.value,
    )

    const rep012Op = buildSessionReport('happy-path', 'OPERATOR', 'ses-012')!
    expect(rep012Op.canExport).toBe(false)

    renderReports('/studio/reports?role=OWNER&hideDevBar=1')
    await waitFor(() => {
      expect(screen.getByText('Combo quà Tết đặc sản vùng cao')).toBeInTheDocument()
    })
    // ses-015 (PREPARING / PENDING) must NOT claim CSV/PDF export is ready
    expect(screen.getByText(/Chưa sẵn sàng xuất \(phiên chưa phát\)/i)).toBeInTheDocument()
    expect(screen.getByText(/Dữ liệu một phần · Chưa mở xuất file/i)).toBeInTheDocument()
    expect(screen.getByText(/Sẵn sàng xuất CSV \/ PDF/i)).toBeInTheDocument()
  })

  it('Gate 2 (FLOW 02 & FLOW 03): Revoking Presenter consent invalidates Session Readiness; Knowledge APPROVED != OCOP VERIFIED', () => {
    const core = getStore('happy-path')

    // FLOW 03: sku-ml-003 has Knowledge APPROVED but OCOP PENDING_REVIEW -> ineligible
    const sku3 = core.products.find((p) => p.skuId === 'sku-ml-003')!
    expect(sku3.knowledgeStatus).toBe('APPROVED')
    expect(sku3.ocopStatus).toBe('PENDING_REVIEW')
    expect(sku3.sessionEligible).toBe(false)

    // FLOW 02: Revoke Linh's rights consent -> ses-014 readiness becomes BLOCKED
    const before = computeReadiness(core, 'ses-014')!
    expect(before.overallReady).toBe(true)

    const linh = core.presenters.find((p) => p.id === 'prs-linh-01')!
    linh.rightsStatus = 'REVOKED'
    recomputeAllSessionReadiness(core)

    const after = computeReadiness(core, 'ses-014')!
    expect(after.overallReady).toBe(false)
    expect(after.gates.some((g) => g.status === 'BLOCKED')).toBe(true)
  })

  it('Gate 2 (FLOW 06 & FLOW 07): Multi-operator assignment independence & PlaybackCompleted ACK deduplication', () => {
    const m03 = getM03Store('happy-path')
    const core = getStore('happy-path')
    const ses014 = core.sessions.find((s) => s.id === 'ses-014')!

    // Both Lan (usr-op-01) and Binh (usr-op-02) assigned to ses-014
    expect(ses014.assignedOperatorIds).toContain('usr-op-01')
    expect(ses014.assignedOperatorIds).toContain('usr-op-02')
    expect(isActorAssignedToSession('happy-path', 'OPERATOR', 'ses-014')).toBe(true)

    // Revoke Binh only -> Lan remains assigned
    ses014.assignedOperatorIds = ses014.assignedOperatorIds.filter((id) => id !== 'usr-op-02')
    const binh = m03.members.find((m) => m.id === 'usr-op-02')!
    binh.assignedSessionIds = binh.assignedSessionIds.filter((id) => id !== 'ses-014')
    expect(isActorAssignedToSession('happy-path', 'OPERATOR', 'ses-014')).toBe(true)

    // PlaybackCompleted ACK advances only at PLAYBACK_COMPLETED and deduplicates
    const snapBefore = buildControlRoomSnapshot('happy-path', 'OWNER', 'ses-014')!
    const countBefore = snapBefore.completedTurnsCount
    for (let i = 0; i < 8; i++) {
      advanceSpeechTurnPhase('happy-path', 'ses-014')
    }
    const snapAfter = buildControlRoomSnapshot('happy-path', 'OWNER', 'ses-014')!
    expect(snapAfter.completedTurnsCount).toBe(countBefore + 1)
  })

  it('Gate 2 (FLOW 10, 11 & 12): Invite revocation ejects guest, session stop moves viewer to STOPPED, and CSV/PDF exports stay safe', () => {
    const m03 = getM03Store('happy-path')
    const core = getStore('happy-path')

    // Viewer snapshot with valid invite
    const validSnap = buildViewerRoomSnapshot('happy-path', 'ses-014', 'ml014-doitac', null)
    expect(validSnap.accessState).toBe('VALID')
    expect(validSnap.lifecycle).toBe('LIVE')

    // Revoking invite blocks access immediately
    const inv = m03.invites.find((i) => i.token === 'ml014-doitac')!
    inv.status = 'REVOKED'
    const revokedSnap = buildViewerRoomSnapshot('happy-path', 'ses-014', 'ml014-doitac', null)
    expect(revokedSnap.accessState).toBe('REVOKED')

    // Other invite on the same session remains VALID (independent)
    const otherSnap = buildViewerRoomSnapshot('happy-path', 'ses-014', 'ml014-dungthu', null)
    expect(otherSnap.accessState).toBe('VALID')

    // Stopping session transitions viewer snapshot lifecycle to STOPPED
    const ses014 = core.sessions.find((s) => s.id === 'ses-014')!
    ses014.lifecycle = 'STOPPED'
    ses014.stoppedAt = '2026-11-21T08:45:00Z'
    const endedSnap = buildViewerRoomSnapshot('happy-path', 'ses-014', 'ml014-dungthu', null)
    expect(endedSnap.lifecycle).toBe('STOPPED')

    // Report reconciles dynamically after stop & sanitizes CSV formulas
    const rep = buildSessionReport('happy-path', 'OWNER', 'ses-014')!
    const sumChart = rep.intervalChart.reduce((s, p) => s + p.admissions, 0)
    expect(sumChart).toBe(rep.kpis.find((k) => k.key === 'guest_successful_admissions')?.value)
    expect(sanitizeCsvCell('=HYPERLINK("http://evil")')).toBe(`"'=HYPERLINK(""http://evil"")"`)
    expect(buildSanitizedAuditCsv(rep).startsWith('\uFEFF')).toBe(true)
    expect(buildSummaryPdfBlob(rep).size).toBeGreaterThan(200)
  })
})
