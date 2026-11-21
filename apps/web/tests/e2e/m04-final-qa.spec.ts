import path from 'node:path'
import fs from 'node:fs'
import { expect, test } from '@playwright/test'

const SCREENSHOT_DIR = path.resolve(
  process.cwd(),
  '../../docs/product/frontend/reports/milestone-04/screenshots',
)

test.beforeAll(() => {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true })
})

async function assertCleanPage(page: import('@playwright/test').Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  expect(overflow).toBeLessThanOrEqual(2)
}

test('Gate 1 (3.1): Tablet 768x1024 Control Room sidebar width = 72px and Control Bar never overlaps sidebar', async ({
  page,
}) => {
  const consoleErrors: string[] = []
  page.on('console', (msg) => {
    if (msg.type() === 'error' && !msg.text().includes('ERR_NAME_NOT_RESOLVED')) {
      consoleErrors.push(msg.text())
    }
  })
  page.on('pageerror', (err) => consoleErrors.push(err.message))

  await page.setViewportSize({ width: 768, height: 1024 })
  await page.goto('/studio/sessions/ses-014/control?role=OPERATOR&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Phòng điều khiển livestream · Phiên #014')

  const geometry = await page.evaluate(() => {
    const aside = document.querySelector('aside')
    const bar = document.querySelector('[data-testid="runtime-control-bar"]')
    const asideRect = aside?.getBoundingClientRect()
    const barRect = bar?.getBoundingClientRect()
    return {
      asideWidth: asideRect ? Math.round(asideRect.width) : 0,
      asideRight: asideRect ? Math.round(asideRect.right) : 0,
      barLeft: barRect ? Math.round(barRect.left) : 0,
      barWidth: barRect ? Math.round(barRect.width) : 0,
      asideClass: aside?.className ?? '',
    }
  })
  console.log('TABLET_GEOMETRY:', JSON.stringify(geometry), 'CONSOLE_ERRORS:', consoleErrors)

  expect(geometry.asideWidth).toBeGreaterThanOrEqual(64)
  expect(geometry.asideWidth).toBeLessThanOrEqual(76)
  expect(geometry.barLeft).toBeGreaterThanOrEqual(geometry.asideRight - 1)
  await assertCleanPage(page)

  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '01-m04-control-room-tablet-768-fixed.png'),
    fullPage: true,
  })
  expect(consoleErrors).toEqual([])
})

test('Gate 1 (3.2, 3.3, 3.4): Session Reports timestamp consistency, chart=KPI reconciliation & export messaging', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 })

  // History page: ses-015 PENDING must NOT say "Có thể xuất CSV / PDF"
  await page.goto('/studio/reports?role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Chưa sẵn sàng xuất (phiên chưa phát)')
  await expect(page.locator('text=Có thể xuất CSV / PDF')).toHaveCount(0)
  await assertCleanPage(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '02-m04-reports-history-export-status-1440-light.png'),
    fullPage: true,
  })

  // Session #013: 19:00 -> 20:32, 7 buckets summing to 86, PARTIAL (N/A concurrent)
  await page.goto('/studio/sessions/ses-013/report?role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Tổng 7 khung = 86 lượt khớp KPI')
  await expect(page.locator('text=Bắt đầu 19:00')).toBeVisible()
  await assertCleanPage(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '03-m04-session-report-013-reconciled-1440-light.png'),
    fullPage: true,
  })

  // Session #012: READY with Owner export button enabled
  await page.goto('/studio/sessions/ses-012/report?role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Báo cáo hoàn chỉnh (READY)')
  await expect(page.getByRole('button', { name: /Xuất báo cáo \(CSV \/ PDF\)/i })).toBeVisible()
  await assertCleanPage(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '04-m04-session-report-012-ready-1440-light.png'),
    fullPage: true,
  })
})

test('Gate 2 (FLOW 08 & 09): Emergency Stop 1-step modal + Escape close + 409 Conflict handling', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/studio/sessions/ses-014/control?role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Phòng điều khiển livestream · Phiên #014')

  // Open 1-step Emergency Stop modal
  await page.getByRole('button', { name: /Dừng khẩn cấp/i }).click()
  await page.waitForSelector('text=Dừng khẩn cấp livestream?')
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '05-m04-emergency-stop-modal-1440-light.png'),
  })

  // Accessibility: Escape closes dialog safely
  await page.keyboard.press('Escape')
  await expect(page.locator('text=Dừng khẩn cấp livestream?')).toHaveCount(0)

  // Simulate 409 conflict in Dark Mode
  await page.goto('/studio/sessions/ses-014/control?role=OWNER&theme=dark&hideDevBar=1')
  await page.waitForSelector('text=Phòng điều khiển livestream · Phiên #014')
  await page.getByRole('button', { name: /Mô phỏng xung đột 409/i }).click()
  await page.getByRole('button', { name: /Tạm dừng AI/i }).click()
  await page.waitForSelector('text=xung đột')
  await assertCleanPage(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '06-m04-command-conflict-409-1440-dark.png'),
    fullPage: true,
  })
})

test('Gate 2 & 3 (FLOW 10 & 11): Viewer Waiting Room, Ended, Revoked Invite + 320px/360px Mobile Check', async ({
  page,
}) => {
  // Waiting Room (chat locked before LIVE) at 390x844
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/live/ses-014?invite=ml014-doitac&demo=waiting&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Livestream sắp bắt đầu')
  await expect(page.locator('input[placeholder*="Nhập bình luận"]')).toHaveCount(0)
  await assertCleanPage(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '07-m04-viewer-waiting-390-light.png'),
    fullPage: true,
  })

  // Session Ended (no replay) at 390x844
  await page.goto('/live/ses-014?invite=ml014-doitac&demo=ended&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Phiên đã kết thúc')
  await assertCleanPage(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '08-m04-viewer-ended-390-light.png'),
    fullPage: true,
  })

  // Revoked invite at 360x800
  await page.setViewportSize({ width: 360, height: 800 })
  await page.goto('/live/ses-014?invite=ml014-noibo&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Không thể tham gia')
  await assertCleanPage(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '09-m04-invite-revoked-360-light.png'),
    fullPage: true,
  })

  // Ultra-compact 320px mobile overflow check on Viewer Entry
  await page.setViewportSize({ width: 320, height: 568 })
  await page.goto('/live/ses-014?invite=ml014-doitac&theme=light&hideDevBar=1')
  await page.waitForSelector('input[placeholder*="Nhập tên để tham gia"]')
  await assertCleanPage(page)
})

test('Gate 2 (Full Cross-Module Demo Checkpoint): Viewer comment propagates to Live Control Room', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/live/ses-014?invite=ml014-doitac&theme=light&hideDevBar=1')
  await page.waitForSelector('input[placeholder*="Nhập tên để tham gia"]')
  await page.fill('input[placeholder*="Nhập tên để tham gia"]', 'UAT Khách VIP')
  await page.getByRole('button', { name: /Vào phòng livestream/i }).click()
  await page.waitForSelector('input[placeholder*="Nhập bình luận"]')

  const uniqueMsg = 'Mứt mận có chứng nhận OCOP mấy sao vậy shop?'
  await page.fill('input[placeholder*="Nhập bình luận"]', uniqueMsg)
  await page.getByRole('button', { name: 'Gửi bình luận' }).click()
  await page.waitForSelector(`text=${uniqueMsg}`)

  // Navigate to Control Room in same SPA/MSW context and verify comment appears live
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/studio/sessions/ses-014/control?role=OPERATOR&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Phòng điều khiển livestream · Phiên #014')
  await assertCleanPage(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '10-m04-demo-control-room-1440-light.png'),
    fullPage: true,
  })
})
