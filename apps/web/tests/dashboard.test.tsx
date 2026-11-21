import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { ThemeProvider } from '@/hooks/useTheme'
import { ScenarioProvider } from '@/hooks/useScenario'
import { AppShell } from '@/app/layouts/AppShell'
import { DashboardPage } from '@/features/dashboard/pages/DashboardPage'

function renderDashboard(search = '') {
  window.history.pushState({}, '', `/studio/dashboard${search}`)
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ScenarioProvider>
          <MemoryRouter initialEntries={[`/studio/dashboard${search}`]}>
            <Routes>
              <Route path="/studio" element={<AppShell />}>
                <Route path="dashboard" element={<DashboardPage />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </ScenarioProvider>
      </ThemeProvider>
    </QueryClientProvider>,
  )
}

describe('Merchant Dashboard — Milestone 1', () => {
  it('renders Owner happy-path with Action Center, Featured Session, Asset Cards, and Create CTA', async () => {
    renderDashboard('?scenario=happy-path&role=OWNER&hideDevBar=1')

    await waitFor(() => {
      expect(screen.getByText('Sẵn sàng cho phiên giới thiệu đặc sản')).toBeInTheDocument()
    })

    expect(screen.getByRole('button', { name: /Tạo phiên mới/i })).toBeInTheDocument()
    expect(screen.getByText('Công việc cần xử lý')).toBeInTheDocument()
    expect(screen.getByText('Kịch bản giới thiệu Mứt Mận Mường Lát')).toBeInTheDocument()
    expect(screen.getByText('Phiên gần nhất')).toBeInTheDocument()
    expect(screen.getByText('Tài nguyên của bạn')).toBeInTheDocument()
    expect(screen.getByText('Phiên livestream gần đây')).toBeInTheDocument()
    // Independent LIVE, AI, Media badges
    expect(screen.getAllByText('Đang phát trực tiếp').length).toBeGreaterThan(0)
    expect(screen.getAllByText('AI đang hoạt động').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Media ổn định').length).toBeGreaterThan(0)
  })

  it('hides Owner-only Create CTA and Admin nav items for Operator role', async () => {
    renderDashboard('?scenario=happy-path&role=OPERATOR&hideDevBar=1')

    await waitFor(() => {
      expect(screen.getByText('Phiên #014 đang phát trực tiếp')).toBeInTheDocument()
    })

    expect(screen.queryByRole('button', { name: /Tạo phiên mới/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Thành viên' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Lời mời xem live' })).not.toBeInTheDocument()
    expect(screen.getByText('Chờ Chủ sở hữu duyệt')).toBeInTheDocument()
  })

  it('shows independent LIVE + AI PAUSED state without treating session as STOPPED', async () => {
    renderDashboard('?scenario=ai-paused&role=OWNER&hideDevBar=1')

    await waitFor(() => {
      expect(screen.getByText(/AI đang tạm dừng trong Phiên #014/i)).toBeInTheDocument()
    })

    expect(screen.getAllByText('Đang phát trực tiếp').length).toBeGreaterThan(0)
    expect(screen.getAllByText('AI đang tạm dừng').length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText('Media ổn định').length).toBeGreaterThan(0)
  })

  it('shows Media DEGRADED fallback warning while keeping session LIVE', async () => {
    renderDashboard('?scenario=media-degraded&role=OWNER&hideDevBar=1')

    await waitFor(() => {
      expect(screen.getByText(/Chất lượng hình ảnh Phiên #014 đang giảm/i)).toBeInTheDocument()
    })

    expect(screen.getAllByText('Media suy giảm').length).toBeGreaterThanOrEqual(2)
    expect(
      screen.getByText(/Đang dùng cảnh sản phẩm dự phòng \+ âm thanh xác minh/i),
    ).toBeInTheDocument()
  })

  it('renders guided empty workspace state', async () => {
    renderDashboard('?scenario=empty&role=OWNER&hideDevBar=1')

    await waitFor(() => {
      expect(screen.getByText('Bắt đầu thiết lập Merchant Studio')).toBeInTheDocument()
    })

    expect(screen.getByText('Chưa có phiên livestream nào')).toBeInTheDocument()
  })

  it('renders error recovery state on API failure', async () => {
    renderDashboard('?scenario=error&role=OWNER&hideDevBar=1')

    await waitFor(() => {
      expect(screen.getByText('Không thể tải dữ liệu tổng quan')).toBeInTheDocument()
    })

    expect(screen.getByRole('button', { name: /Thử tải lại/i })).toBeInTheDocument()
  })

  it('renders permission-denied state on 403', async () => {
    renderDashboard('?scenario=permission-denied&role=OPERATOR&hideDevBar=1')

    await waitFor(() => {
      expect(
        screen.getByText('Bạn không có quyền truy cập phạm vi này'),
      ).toBeInTheDocument()
    })
  })
})
