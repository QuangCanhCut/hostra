import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { ThemeProvider } from '@/hooks/useTheme'
import { ScenarioProvider } from '@/hooks/useScenario'
import { AppShell } from '@/app/layouts/AppShell'
import { SessionWizardPage } from '@/features/live-session/pages/SessionWizardPage'
import { MembersPage } from '@/features/members/pages/MembersPage'
import { LiveControlRoomPage } from '@/features/control-room/pages/LiveControlRoomPage'
import { InvitesPage } from '@/features/invitations/pages/InvitesPage'
import { ViewerLiveRoomPage } from '@/features/viewer/pages/ViewerLiveRoomPage'
import { ReportsHistoryPage } from '@/features/reports/pages/ReportsHistoryPage'
import { SessionReportPage } from '@/features/reports/pages/SessionReportPage'
import { buildSanitizedAuditCsv, buildSummaryPdfBlob, sanitizeCsvCell } from '@/lib/export-utils'
import { buildSessionReport } from '@/mocks/m03.store'

function renderM03(initialUrl: string) {
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
              <Route path="/live/:id" element={<ViewerLiveRoomPage />} />
              <Route path="/studio" element={<AppShell />}>
                <Route path="sessions/new" element={<SessionWizardPage />} />
                <Route path="sessions/:id/control" element={<LiveControlRoomPage />} />
                <Route path="sessions/:id/invites" element={<InvitesPage />} />
                <Route path="sessions/:id/report" element={<SessionReportPage />} />
                <Route path="members" element={<MembersPage />} />
                <Route path="invites" element={<InvitesPage />} />
                <Route path="reports" element={<ReportsHistoryPage />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </ScenarioProvider>
      </ThemeProvider>
    </QueryClientProvider>,
  )
}

function readBlobAsText(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result ?? ''))
    reader.onerror = () => reject(reader.error)
    reader.readAsText(blob)
  })
}

describe('Milestone 03 + Addendum — End-to-End Mock Workflows & Invariants', () => {
  it('Addendum #1 (SKU Picker Fix): loads product catalog before rendering picker and syncs SKU count', async () => {
    renderM03('/studio/sessions/new?role=OWNER&hideDevBar=1')

    await waitFor(() => {
      expect(screen.getByText(/Kho sản phẩm \(/i)).toBeInTheDocument()
    })
    expect(screen.queryByText(/Kho sản phẩm \(0 SKU\)/i)).not.toBeInTheDocument()
    expect(screen.getByText(/Đạt số lượng 2–5/i)).toBeInTheDocument()
  })

  it('M03-B (Members & Permissions): Owner sees N:N assignments; Operator is blocked from member management', async () => {
    const { unmount } = renderM03('/studio/members?role=OWNER&hideDevBar=1')

    await waitFor(() => {
      expect(screen.getAllByText('Trần Ngọc Lan').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Lê Thanh Bình').length).toBeGreaterThan(0)
    })
    unmount()

    renderM03('/studio/members?role=OPERATOR&hideDevBar=1')
    await waitFor(() => {
      expect(screen.getByText(/Chỉ Chủ sở hữu mới có quyền/i)).toBeInTheDocument()
    })
  })

  it('M03-A (Live Control Room): PAUSE_AI keeps session LIVE and shows Resume AI action', async () => {
    const user = userEvent.setup()
    renderM03('/studio/sessions/ses-014/control?role=OWNER&hideDevBar=1')

    await waitFor(() => {
      expect(screen.getByText(/Phòng điều khiển livestream · Phiên #014/i)).toBeInTheDocument()
    })

    const pauseBtn = screen.getByRole('button', { name: /Tạm dừng AI/i })
    await user.click(pauseBtn)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Tiếp tục AI/i })).toBeInTheDocument()
    })
    // Session must remain LIVE (not STOPPED)
    expect(screen.getAllByText(/Đang phát trực tiếp/i).length).toBeGreaterThan(0)
  })

  it('M03-C (Invite Management): Owner sees named invites & create CTA; Operator is restricted from managing invites', async () => {
    const { unmount } = renderM03('/studio/sessions/ses-014/invites?role=OWNER&hideDevBar=1')

    await waitFor(() => {
      expect(screen.getAllByText(/Đối tác phân phối/i).length).toBeGreaterThan(0)
      expect(screen.getByRole('button', { name: /Tạo lời mời mới/i })).toBeInTheDocument()
    })
    unmount()

    renderM03('/studio/sessions/ses-014/invites?role=OPERATOR&hideDevBar=1')
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /Tạo lời mời mới/i })).not.toBeInTheDocument()
    })
  })

  it('M03-D (Viewer Live Room): renders standalone without Merchant AppShell and admits viewer with nickname', async () => {
    const user = userEvent.setup()
    renderM03('/live/ses-014?invite=ml014-doitac&hideDevBar=1')

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Nhập tên để tham gia/i)).toBeInTheDocument()
    })
    // Must NOT show Merchant AppShell navigation
    expect(screen.queryByText('Thành viên & Phân quyền')).not.toBeInTheDocument()

    await user.type(screen.getByPlaceholderText(/Nhập tên để tham gia/i), 'Minh Khang')
    await user.click(screen.getByRole('button', { name: /Vào phòng livestream/i }))

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Nhập bình luận/i)).toBeInTheDocument()
    })
  })

  it('M03-E (Session Reports & Export Security): neutralizes CSV formulas, builds valid PDF 1.4, and enforces Owner-only export', async () => {
    // 1. CSV Formula Injection sanitization
    expect(sanitizeCsvCell('=CMD("calc")')).toBe(`"'=CMD(""calc"")"`)
    expect(sanitizeCsvCell('+1+1')).toBe(`"'+1+1"`)
    expect(sanitizeCsvCell('-2+3')).toBe(`"'-2+3"`)
    expect(sanitizeCsvCell('@SUM(A1)')).toBe(`"'@SUM(A1)"`)
    expect(sanitizeCsvCell('Normal text')).toBe(`"Normal text"`)

    // 2. Valid PDF 1.4 structure
    const report = buildSessionReport('happy-path', 'OWNER', 'ses-013')
    expect(report).not.toBeNull()
    const csv = buildSanitizedAuditCsv(report!)
    expect(csv.startsWith('\uFEFF"timestamp_utc"')).toBe(true)

    const pdfBlob = buildSummaryPdfBlob(report!)
    const pdfText = await readBlobAsText(pdfBlob)
    expect(pdfText.startsWith('%PDF-1.4')).toBe(true)
    expect(pdfText.includes('%%EOF')).toBe(true)

    // 3. UI check: ses-013 shows PARTIAL + N/A honestly; ses-014 READY lets Owner export, hides for Operator
    const { unmount: unmountPartial } = renderM03('/studio/sessions/ses-013/report?role=OWNER&hideDevBar=1')
    await waitFor(() => {
      expect(screen.getByText(/Dữ liệu một phần \(PARTIAL\)/i)).toBeInTheDocument()
      expect(screen.getAllByText(/N\/A/i).length).toBeGreaterThan(0)
      expect(screen.getAllByText(/PlaybackCompleted ACK/i).length).toBeGreaterThan(0)
    })
    unmountPartial()

    const { unmount } = renderM03('/studio/sessions/ses-014/report?role=OWNER&hideDevBar=1')
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Xuất báo cáo \(CSV \/ PDF\)/i })).toBeInTheDocument()
    })
    unmount()

    renderM03('/studio/sessions/ses-014/report?role=OPERATOR&hideDevBar=1')
    await waitFor(() => {
      expect(screen.getByText(/Chế độ xem rút gọn dành cho Vận hành viên/i)).toBeInTheDocument()
    })
    expect(
      screen.queryByRole('button', { name: /Xuất báo cáo \(CSV \/ PDF\)/i }),
    ).not.toBeInTheDocument()
  })
})
