import path from 'node:path'
import fs from 'node:fs'
import { expect, test } from '@playwright/test'

const SCREENSHOT_DIR = path.resolve(
  process.cwd(),
  '../../docs/product/frontend/reports/milestone-02/screenshots',
)

test.beforeAll(() => {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true })
})

async function assertLayoutHealth(page: import('@playwright/test').Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  expect(overflow).toBeLessThanOrEqual(2)

  // Verify no visible table cell is squished below 64px width (M01-FIX-02 regression guard)
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

test('M01 Regression + Fixes: Tablet 768x1024 cards & Media Degraded synced', async ({ page }) => {
  await page.setViewportSize({ width: 768, height: 1024 })
  await page.goto('/studio/dashboard?scenario=media-degraded&role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Chất lượng hình ảnh Phiên #014 đang giảm')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '01-dashboard-m01fix-tablet-768-light.png'),
    fullPage: true,
  })

  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/studio/dashboard?scenario=happy-path&role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Sẵn sàng cho phiên giới thiệu đặc sản')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '02-dashboard-m01fix-mobile-390-light.png'),
    fullPage: true,
  })
})

test('Flow A — AI Presenter Studio (Library, Wizard 3 Styles, A/B Detail, Rights Portal)', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/studio/presenters?role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Thư viện AI Presenter')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '03-presenter-library-1440-light.png'),
    fullPage: true,
  })

  await page.goto('/studio/presenters/new?role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Tạo AI Presenter mới')
  await page.click('text=Phong cách & Giọng')
  await page.waitForSelector('text=Chọn 1 trong 3 phong cách trình diễn')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '04-presenter-wizard-styles-1440-light.png'),
    fullPage: true,
  })

  await page.goto('/studio/presenters/prs-linh-01?role=OWNER&theme=dark&hideDevBar=1')
  await page.waitForSelector('text=So sánh phiên bản Video A / B')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '05-presenter-ab-compare-1440-dark.png'),
    fullPage: true,
  })

  await page.goto('/rights/consent/req-consent-an-03?theme=light')
  await page.waitForSelector('text=Xác nhận quyền sử dụng hình ảnh cá nhân')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '06-rights-consent-portal-1440-light.png'),
    fullPage: true,
  })
})

test('Flow B & C — Products & OCOP + Knowledge & Claims (Light & Dark)', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/studio/products?role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Sản phẩm & Hồ sơ OCOP')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '07-products-catalog-1440-light.png'),
    fullPage: true,
  })

  await page.goto('/studio/products/sku-ml-003?tab=ocop&role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Tài liệu chứng cứ OCOP & Thực phẩm')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '08-product-ocop-evidence-1440-light.png'),
    fullPage: true,
  })

  await page.goto('/studio/knowledge/sku-ml-001?role=OWNER&theme=dark&hideDevBar=1')
  await page.waitForSelector('text=Duyệt thông tin · Mứt Mận Mường Lát')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '09-knowledge-review-1440-dark.png'),
    fullPage: true,
  })
})

test('Flow D, E, F — Story Planner AI Edit, SKU Picker, Readiness & Operator Restrictions', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/studio/sessions/ses-015/story?role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Lập kế hoạch nội dung · Phiên #015')
  await page.click('button:has-text("Gửi yêu cầu đến Trợ lý AI")')
  await page.waitForSelector('text=Đề xuất thay đổi (Trước / Sau)')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '10-story-planner-ai-diff-1440-light.png'),
    fullPage: true,
  })

  await page.setViewportSize({ width: 1920, height: 1080 })
  await page.goto('/studio/sessions/new?role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Sản phẩm trong phiên (3/5 SKU)')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '11-session-sku-picker-1920-light.png'),
    fullPage: true,
  })

  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/studio/sessions/ses-015/readiness?role=OWNER&theme=dark&hideDevBar=1')
  await page.waitForSelector('text=Kiểm tra sẵn sàng · Phiên #015')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '12-readiness-blocked-1440-dark.png'),
    fullPage: true,
  })

  // Mobile 375x812 check on Readiness + Operator role restriction
  await page.setViewportSize({ width: 375, height: 812 })
  await page.goto('/studio/sessions/ses-015/readiness?role=OPERATOR&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Chỉ Chủ sở hữu được Bắt đầu')
  await assertLayoutHealth(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '13-readiness-operator-mobile-375-light.png'),
    fullPage: true,
  })
})
