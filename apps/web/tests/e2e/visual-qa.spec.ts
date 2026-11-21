import path from 'node:path'
import fs from 'node:fs'
import { expect, test } from '@playwright/test'

const SCREENSHOT_DIR = path.resolve(
  process.cwd(),
  '../../docs/product/frontend/reports/milestone-01/screenshots',
)

test.beforeAll(() => {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true })
})

async function assertNoHorizontalOverflow(page: import('@playwright/test').Page) {
  const overflow = await page.evaluate(() => {
    return document.documentElement.scrollWidth - document.documentElement.clientWidth
  })
  expect(overflow).toBeLessThanOrEqual(2)
}

test('Desktop 1440x900 — Dashboard Light & Dark (Owner happy-path)', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/studio/dashboard?scenario=happy-path&role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Sẵn sàng cho phiên giới thiệu đặc sản')
  await page.waitForLoadState('networkidle')
  await assertNoHorizontalOverflow(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '01-dashboard-desktop-1440-light.png'),
    fullPage: true,
  })

  await page.goto('/studio/dashboard?scenario=happy-path&role=OWNER&theme=dark&hideDevBar=1')
  await page.waitForSelector('text=Sẵn sàng cho phiên giới thiệu đặc sản')
  await assertNoHorizontalOverflow(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '02-dashboard-desktop-1440-dark.png'),
    fullPage: true,
  })
})

test('Desktop 1920x1080 — Operator role & Media Degraded state', async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 })
  await page.goto('/studio/dashboard?scenario=happy-path&role=OPERATOR&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Phiên #014 đang phát trực tiếp')
  await assertNoHorizontalOverflow(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '03-dashboard-operator-1920-light.png'),
    fullPage: true,
  })

  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/studio/dashboard?scenario=media-degraded&role=OWNER&theme=dark&hideDevBar=1')
  await page.waitForSelector('text=Chất lượng hình ảnh Phiên #014 đang giảm')
  await assertNoHorizontalOverflow(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '04-dashboard-media-degraded-dark.png'),
    fullPage: true,
  })
})

test('Tablet 768x1024 & Mobile 390x844 / 375x812 responsive checks', async ({ page }) => {
  await page.setViewportSize({ width: 768, height: 1024 })
  await page.goto('/studio/dashboard?scenario=happy-path&role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Sẵn sàng cho phiên giới thiệu đặc sản')
  await assertNoHorizontalOverflow(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '05-dashboard-tablet-768-light.png'),
    fullPage: true,
  })

  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/studio/dashboard?scenario=happy-path&role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Sẵn sàng cho phiên giới thiệu đặc sản')
  await assertNoHorizontalOverflow(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '06-dashboard-mobile-390-light.png'),
    fullPage: true,
  })

  await page.setViewportSize({ width: 375, height: 812 })
  await page.goto('/studio/dashboard?scenario=empty&role=OWNER&theme=dark&hideDevBar=1')
  await page.waitForSelector('text=Bắt đầu thiết lập Merchant Studio')
  await assertNoHorizontalOverflow(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '07-dashboard-empty-mobile-375-dark.png'),
    fullPage: true,
  })
})

test('Error & Sign-in screens visual verification', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/studio/dashboard?scenario=error&role=OWNER&theme=light&hideDevBar=1')
  await page.waitForSelector('text=Không thể tải dữ liệu tổng quan')
  await assertNoHorizontalOverflow(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '08-dashboard-error-light.png'),
    fullPage: true,
  })

  await page.goto('/auth/sign-in?theme=light')
  await page.waitForSelector('text=Đăng nhập vào Merchant Studio')
  await assertNoHorizontalOverflow(page)
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, '09-auth-signin-light.png'),
    fullPage: true,
  })
})
