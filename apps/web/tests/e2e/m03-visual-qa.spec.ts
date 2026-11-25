import path from 'node:path'
import fs from 'node:fs'
import { expect, test } from '@playwright/test'

const SCREENSHOT_DIR = path.resolve(
  process.cwd(),
  '../../docs/product/frontend/reports/milestone-03/screenshots',
)

test.beforeAll(() => {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true })
})

async function assertLayoutHealth(page: import('@playwright/test').Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  expect(overflow).toBeLessThanOrEqual(2)

  const minCellWidth = await page.evaluate(() => {
    const cells = Array.from(document.querySelectorAll('table th, table td')).filter((el) => {
      const style = window.getComputedStyle(el)
      return style.display !== 'none' && el.getBoundingClientRect().width > 0
    })
    if (cells.length === 0) return 999
    return Math.min(...cells.map((el) => el.getBoundingClientRect().width))
  })
  expect(minCellWidth).toBeGreaterThanOrEqual(64)
}

test('Addendum #1 & #2: SKU Picker loaded catalog (1920x1080) & Presenter A/B polish', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1920, height: 1080 })
  await page.goto('/studio/sessions/new?role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Kho sản phẩm (')
  await expect(page.locator('text=Kho sản phẩm (0 SKU)')).toHaveCount(0)
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '01-addendum-sku-picker-fixed-1920-light.png'),
    fullPage: true,
  })

  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/studio/presenters/prs-linh-01?role=OWNER&theme=dark&hideDevBar=1')
  await page.waitForSelector('text=Bản A · v1')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '02-addendum-presenter-ab-1440-dark.png'),
    fullPage: true,
  })
})

test('M03-A: Live Control Room (Desktop 1440 Light & Dark + Tablet 768 + Pause AI)', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/studio/sessions/ses-014/control?role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Phòng điều khiển livestream · Phiên #014')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '03-control-room-live-1440-light.png'),
    fullPage: true,
  })

  // Pause AI -> LIVE stays active, button switches to Tiếp tục AI
  await page.getByRole('button', { name: /Tạm dừng AI/i }).click()
  await page.waitForSelector('button:has-text("Tiếp tục AI")')
  await page.goto('/studio/sessions/ses-014/control?role=OWNER&theme=dark&hideDevBar=1')
  await page.waitForSelector('text=Phòng điều khiển livestream · Phiên #014')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '04-control-room-live-1440-dark.png'),
    fullPage: true,
  })

  await page.setViewportSize({ width: 768, height: 1024 })
  await page.goto('/studio/sessions/ses-014/control?role=OPERATOR&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Phòng điều khiển livestream · Phiên #014')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '05-control-room-operator-768-light.png'),
    fullPage: true,
  })
})

test('M03-B: Members & Permissions (Owner 1440 Light & Operator restricted)', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/studio/members?role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Trần Ngọc Lan')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '06-members-owner-1440-light.png'),
    fullPage: true,
  })

  await page.goto('/studio/members?role=OPERATOR&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Chỉ Chủ sở hữu')
  await assertLayoutHealth(page)
})

test('M03-C: Invite Management & Real Scannable QR (1440 Light)', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/studio/sessions/ses-014/invites?role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Đối tác phân phối')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '07-invites-qr-1440-light.png'),
    fullPage: true,
  })
})

test('M03-D: Viewer Live Room — Mobile 390x844 & 375x812 (Entry, Live Room, Comment, No AppShell)', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/live/ses-014?invite=ml014-doitac&theme=light&hideDevBar=1')
  await page.waitForSelector('input[placeholder*="Nhập tên để tham gia"]')
  await expect(page.locator('text=Thành viên & Phân quyền')).toHaveCount(0)
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '08-viewer-entry-390-light.png'),
    fullPage: true,
  })

  await page.fill('input[placeholder*="Nhập tên để tham gia"]', 'Minh Khang')
  await page.getByRole('button', { name: /Vào phòng livestream/i }).click()
  await page.waitForSelector('input[placeholder*="Nhập bình luận"]')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '09-viewer-live-390-light.png'),
    fullPage: true,
  })

  await page.setViewportSize({ width: 375, height: 812 })
  await page.goto('/live/ses-014?invite=ml014-doitac&theme=dark&hideDevBar=1')
  await page.waitForSelector('input[placeholder*="Nhập tên để tham gia"]')
  await page.fill('input[placeholder*="Nhập tên để tham gia"]', 'Lan Anh')
  await page.getByRole('button', { name: /Vào phòng livestream/i }).click()
  await page.waitForSelector('input[placeholder*="Nhập bình luận"]')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '10-viewer-live-375-dark.png'),
    fullPage: true,
  })
})

test('M03-E: Session Reports & History (Owner 1440 Light/Dark + Operator Reduced View)', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/studio/reports?role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Báo cáo & Lịch sử phiên livestream')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '11-reports-history-1440-light.png'),
    fullPage: true,
  })

  await page.goto('/studio/sessions/ses-013/report?role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=PlaybackCompleted ACK')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '12-session-report-owner-1440-light.png'),
    fullPage: true,
  })

  await page.goto('/studio/sessions/ses-013/report?role=OPERATOR&theme=dark&hideDevBar=1')
  await page.waitForSelector('text=Chế độ xem rút gọn dành cho Vận hành viên')
  await expect(page.getByRole('button', { name: /Xuất báo cáo/i })).toHaveCount(0)
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '13-session-report-operator-1440-dark.png'),
    fullPage: true,
  })
})
