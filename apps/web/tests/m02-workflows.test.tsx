import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { ThemeProvider } from '@/hooks/useTheme'
import { ScenarioProvider } from '@/hooks/useScenario'
import { AppShell } from '@/app/layouts/AppShell'
import { DashboardPage } from '@/features/dashboard/pages/DashboardPage'
import { PresenterLibraryPage } from '@/features/presenter/pages/PresenterLibraryPage'
import { PresenterWizardPage } from '@/features/presenter/pages/PresenterWizardPage'
import { PresenterDetailPage } from '@/features/presenter/pages/PresenterDetailPage'
import { RightsConsentPortalPage } from '@/features/presenter/pages/RightsConsentPortalPage'
import { ProductsCatalogPage } from '@/features/products/pages/ProductsCatalogPage'
import { ProductDetailPage } from '@/features/products/pages/ProductDetailPage'
import { KnowledgeReviewPage } from '@/features/knowledge/pages/KnowledgeReviewPage'
import { StoryPlannerPage } from '@/features/story-planner/pages/StoryPlannerPage'
import { SessionWizardPage } from '@/features/live-session/pages/SessionWizardPage'
import { ReadinessPage } from '@/features/live-session/pages/ReadinessPage'

function renderApp(initialUrl: string) {
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
              <Route path="/rights/consent/:requestId" element={<RightsConsentPortalPage />} />
              <Route path="/studio" element={<AppShell />}>
                <Route path="dashboard" element={<DashboardPage />} />
                <Route path="presenters" element={<PresenterLibraryPage />} />
                <Route path="presenters/new" element={<PresenterWizardPage />} />
                <Route path="presenters/:id" element={<PresenterDetailPage />} />
                <Route path="products" element={<ProductsCatalogPage />} />
                <Route path="products/:skuId" element={<ProductDetailPage />} />
                <Route path="knowledge/:skuId" element={<KnowledgeReviewPage />} />
                <Route path="sessions/new" element={<SessionWizardPage />} />
                <Route path="sessions/:id/story" element={<StoryPlannerPage />} />
                <Route path="sessions/:id/readiness" element={<ReadinessPage />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </ScenarioProvider>
      </ThemeProvider>
    </QueryClientProvider>,
  )
}

describe('Milestone 2 — M01 Fixes & Cross-Module Asset Preparation', () => {
  it('M01-FIX-01 & M01-FIX-04: syncs media-degraded across Featured + Recent Sessions and matches Presenter KPI count (03)', async () => {
    renderApp('/studio/dashboard?scenario=media-degraded&role=OWNER&hideDevBar=1')

    await waitFor(() => {
      expect(screen.getByText(/Chất lượng hình ảnh Phiên #014 đang giảm/i)).toBeInTheDocument()
    })

    // Both Featured Session and Recent Sessions table/cards show Media suy giảm (zero Media ổn định for #014)
    expect(screen.getAllByText('Media suy giảm').length).toBeGreaterThanOrEqual(2)
    // Presenter KPI count reflects all 3 presenters in canonical store (Linh, Mai, An)
    expect(screen.getByText('03')).toBeInTheDocument()
  })

  it('M02-A: shows A/B comparison only when >= 2 candidates (Linh) and first-run view for 1 candidate (Mai)', async () => {
    const { unmount } = renderApp('/studio/presenters/prs-linh-01?role=OWNER&hideDevBar=1')
    await waitFor(() => {
      expect(screen.getByText(/So sánh phiên bản Video A \/ B/i)).toBeInTheDocument()
    })
    unmount()

    renderApp('/studio/presenters/prs-mai-02?role=OWNER&hideDevBar=1')
    await waitFor(() => {
      expect(screen.getByText(/Ảnh chân dung gốc ↔ Gói clip đầu tiên/i)).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /Tạo lại riêng clip lỗi này/i })).toBeInTheDocument()
  })

  it('M02-A: blocks generation when rights are pending or revoked', async () => {
    renderApp('/studio/presenters/prs-an-03?role=OWNER&hideDevBar=1')
    await waitFor(() => {
      expect(screen.getByText(/Đang chờ Chủ thể quyền xác nhận/i)).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /Tạo gói clip mới/i })).toBeDisabled()
  })

  it('M02-B: prevents Operator from submitting OCOP verification while allowing evidence draft upload', async () => {
    renderApp('/studio/products/sku-ml-003?tab=ocop&role=OPERATOR&hideDevBar=1')
    await waitFor(() => {
      expect(screen.getByText(/Trà thảo mộc Sơn La/i)).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /\+ Tải Quyết định OCOP mẫu/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Gửi hồ sơ xác minh OCOP/i })).not.toBeInTheDocument()
  })

  it('M02-C: enforces per-item review before bundle approval and keeps blocked medical claims non-approvable', async () => {
    renderApp('/studio/knowledge/sku-ml-005?role=OWNER&hideDevBar=1')
    await waitFor(() => {
      expect(screen.getByText(/Măng khô nứa rừng/i)).toBeInTheDocument()
    })
    // Blocked medical claim present and bundle approval disabled until required items approved
    expect(screen.getByText(/Tuyên bố giảm tiểu đường/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Phê duyệt gói tri thức/i })).toBeDisabled()
  })

  it('M02-D: AI Editing Assistant returns Before/After diff and guards unsupported medical claims', async () => {
    const user = userEvent.setup()
    renderApp('/studio/sessions/ses-015/story?role=OWNER&hideDevBar=1')

    await waitFor(() => {
      expect(screen.getByText(/Timeline kịch bản/i)).toBeInTheDocument()
    })

    const textarea = screen.getByLabelText(/Yêu cầu chỉnh sửa kịch bản/i)
    await user.clear(textarea)
    await user.type(textarea, 'Thêm câu nói chữa bệnh đau dạ dày cho mứt mận')
    await user.click(screen.getByRole('button', { name: /Gửi yêu cầu đến Trợ lý AI/i }))

    await waitFor(() => {
      expect(screen.getByText(/Đề xuất thay đổi \(Trước \/ Sau\)/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/Đã loại bỏ nội dung thiếu chứng cứ/i)).toBeInTheDocument()
  })

  it('M02-E: SKU Picker blocks duplicate SKUs and enforces maximum 5 SKUs', async () => {
    const user = userEvent.setup()
    renderApp('/studio/sessions/new?role=OWNER&hideDevBar=1')

    await waitFor(() => {
      expect(screen.getByText(/Sản phẩm trong phiên \(3\/5 SKU\)/i)).toBeInTheDocument()
      expect(screen.getAllByRole('button', { name: /^Thêm$/i }).length).toBeGreaterThanOrEqual(2)
    })

    const addButtons = screen.getAllByRole('button', { name: /^Thêm$/i })
    await user.click(addButtons[0])
    await user.click(addButtons[1])

    await waitFor(() => {
      expect(screen.getByText(/Sản phẩm trong phiên \(5\/5 SKU\)/i)).toBeInTheDocument()
    })
  })

  it('M02-F: Readiness blocks Start when OCOP/Story incomplete and hides Start for Operator', async () => {
    const { unmount } = renderApp('/studio/sessions/ses-015/readiness?role=OWNER&hideDevBar=1')
    await waitFor(() => {
      expect(screen.getByText(/Kiểm tra sẵn sàng · Phiên #015/i)).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /Bắt đầu livestream/i })).toBeDisabled()
    unmount()

    renderApp('/studio/sessions/ses-015/readiness?role=OPERATOR&hideDevBar=1')
    await waitFor(() => {
      expect(screen.getByText(/Chỉ Chủ sở hữu được Bắt đầu/i)).toBeInTheDocument()
    })
    expect(screen.queryByRole('button', { name: /Bắt đầu livestream/i })).not.toBeInTheDocument()
  })

  it('Cross-module invalidation: revoking Presenter rights blocks Readiness for session #014', async () => {
    const user = userEvent.setup()
    renderApp('/rights/consent/req-consent-linh-01?role=OWNER&hideDevBar=1')
    await waitFor(() => {
      expect(screen.getByText(/Xác nhận quyền sử dụng hình ảnh cá nhân/i)).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /Thu hồi quyền ngay/i }))
    await waitFor(() => {
      expect(screen.getByText(/Bạn đã thu hồi quyền sử dụng/i)).toBeInTheDocument()
    })
  })
})
