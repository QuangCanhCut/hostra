import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ThemeProvider } from '@/hooks/useTheme'
import { ScenarioProvider } from '@/hooks/useScenario'
import { AppShell } from '@/app/layouts/AppShell'
import { DashboardPage } from '@/features/dashboard/pages/DashboardPage'
import { OnboardingPage } from '@/features/workspace/pages/OnboardingPage'
import { SignInPage } from '@/features/auth/pages/SignInPage'
import { SessionReportPage } from '@/features/reports/pages/SessionReportPage'
import { resetStore } from '@/mocks/store'
import { resetM03Store } from '@/mocks/m03.store'

/* Kiểm thử hồi quy M05.4: PO-D01 Account Dropdown Menu, UX-04 không lồng interactive, PO-D02 microcopy thân thiện */
function renderAt(initialEntry: string) {
  window.history.pushState({}, '', initialEntry)
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0 },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ScenarioProvider>
          <MemoryRouter initialEntries={[initialEntry]}>
            <Routes>
              <Route path="/auth/sign-in" element={<SignInPage />} />
              <Route path="/studio" element={<AppShell />}>
                <Route path="dashboard" element={<DashboardPage />} />
                <Route path="onboarding" element={<OnboardingPage />} />
                <Route path="sessions/:id/report" element={<SessionReportPage />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </ScenarioProvider>
      </ThemeProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  resetStore('happy-path')
  resetM03Store('happy-path')
  window.localStorage.clear()
})

afterEach(() => {
  cleanup()
})

describe('M05.4 — Đóng vấn đề UX & PO Decisions', () => {
  it('PO-D01: Mở Account Dropdown Menu từ Avatar, đóng bằng Escape và khôi phục focus', async () => {
    const user = userEvent.setup()
    renderAt('/studio/dashboard?role=OWNER&scenario=happy-path&hideDevBar=1')

    const trigger = await screen.findByRole('button', { name: /Menu tài khoản/i })
    expect(trigger).toHaveAttribute('aria-expanded', 'false')

    await user.click(trigger)
    expect(trigger).toHaveAttribute('aria-expanded', 'true')

    const menu = screen.getByRole('menu', { name: /Tùy chọn tài khoản/i })
    expect(menu).toBeInTheDocument()
    expect(
      screen.getByRole('menuitem', { name: /Thiết lập không gian làm việc/i }),
    ).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: /Đăng xuất/i })).toBeInTheDocument()

    await user.keyboard('{Escape}')
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })

  it('PO-D01: Bấm Thiết lập không gian làm việc và Đăng xuất (mock) điều hướng đúng', async () => {
    const user = userEvent.setup()
    renderAt('/studio/dashboard?role=OWNER&scenario=happy-path&hideDevBar=1')

    const trigger = await screen.findByRole('button', { name: /Menu tài khoản/i })
    await user.click(trigger)
    await user.click(screen.getByRole('menuitem', { name: /Thiết lập không gian làm việc/i }))

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: /Thiết lập không gian làm việc/i }),
      ).toBeInTheDocument()
    })

    const trigger2 = screen.getByRole('button', { name: /Menu tài khoản/i })
    await user.click(trigger2)
    await user.click(screen.getByRole('menuitem', { name: /Đăng xuất/i }))

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /Tiếp tục với vai trò Chủ sở hữu/i }),
      ).toBeInTheDocument()
    })
  })

  it('UX-04: Dashboard không còn bất kỳ phần tử tương tác lồng nhau nào (a button, button a)', async () => {
    const { container } = renderAt('/studio/dashboard?role=OWNER&scenario=happy-path&hideDevBar=1')

    await screen.findByRole('heading', { name: /Tổng quan/i })
    await waitFor(() => {
      expect(screen.getByText(/Công việc cần xử lý/i)).toBeInTheDocument()
    })

    const nested = container.querySelectorAll('a button, button a, a a, button button')
    expect(nested.length).toBe(0)
  })

  it('PO-D02 / UX-06: Báo cáo phiên hiển thị nguồn đo tiếng Việt thân thiện, không lộ mã nội bộ P04/P09/LiveKit Presence', async () => {
    renderAt('/studio/sessions/ses-013/report?role=OWNER&hideDevBar=1')

    await waitFor(() => {
      expect(screen.getByText(/Hệ thống quản lý phiên phát/i)).toBeInTheDocument()
      expect(screen.getByText(/Xác nhận nội dung đã phát tới người xem/i)).toBeInTheDocument()
      expect(screen.getByText(/Dữ liệu theo dõi người xem trực tiếp/i)).toBeInTheDocument()
    })

    expect(screen.queryByText(/P09 Session Lifecycle/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/LiveKit Presence Telemetry/i)).not.toBeInTheDocument()
  })
})
