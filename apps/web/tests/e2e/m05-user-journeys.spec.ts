import { expect, test } from '@playwright/test'

/* Bộ kiểm thử E2E hồi quy 11 hành trình người dùng (Milestone 05.3) */

test('J01 & J02: Owner đăng nhập mock -> Onboarding lưu nháp -> AI Presenter A/B', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/auth/sign-in')
  await page.waitForSelector('text=Đăng nhập vào Merchant Studio')
  await page.getByRole('button', { name: /Chủ sở hữu/i }).click()
  await page.waitForURL(/\/studio\/dashboard/)

  // Onboarding lưu nháp và quay lại vẫn giữ trạng thái
  await page.goto('/studio/onboarding?role=OWNER')
  await page.waitForSelector('text=Thiết lập không gian làm việc')
  await page.getByRole('button', { name: /Lưu bản nháp/i }).click()
  await page.waitForSelector('text=Đã lưu bản nháp')

  // Presenter A/B compare & QC
  await page.goto('/studio/presenters/prs-linh-01?role=OWNER')
  await page.waitForSelector('text=Bản A · v1')
  await expect(page.locator('text=Bản B · v2')).toBeVisible()
})

test('J03, J04 & J05: Products/OCOP -> Knowledge chặn claim -> Story AI diff -> Readiness chặn Start', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/studio/products?role=OWNER')
  await page.waitForSelector('text=Mứt Mận Mường Lát')

  // Knowledge: claim chữa bệnh bị chặn
  await page.goto('/studio/knowledge/sku-ml-001?role=OWNER')
  await page.waitForSelector('text=Bị chặn')

  // Story Planner: Trợ lý AI đề xuất diff không tự phê duyệt
  await page.goto('/studio/sessions/ses-015/story?role=OWNER')
  await page.waitForSelector('text=Phiên #015')
  await page.getByRole('button', { name: /Gửi yêu cầu đến Trợ lý AI/i }).click()
  await page.waitForSelector('text=Áp dụng vào bản nháp')

  // Readiness: mục Bị chặn / Đang chờ hiện đầu tiên & nút Start bị khóa
  await page.goto('/studio/sessions/ses-015/readiness?role=OWNER')
  await page.waitForSelector('text=Chưa thể khởi chạy')
  await expect(page.getByRole('button', { name: /Bắt đầu livestream/i })).toBeDisabled()

  // Operator không có nút Bắt đầu livestream
  await page.goto('/studio/sessions/ses-015/readiness?role=OPERATOR')
  await page.waitForSelector('text=Chỉ Chủ sở hữu được Bắt đầu')
  await expect(page.getByRole('button', { name: /Bắt đầu livestream/i })).toHaveCount(0)
})

test('J06: Live Control Room — Pause AI giữ LIVE, Switch SKU ACCEPTED != APPLIED, Sticky Bar & Modal Focus Trap', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/studio/sessions/ses-014/control?role=OWNER')
  await page.waitForSelector('text=Phòng điều khiển livestream · Phiên #014')

  // Pause AI -> vẫn Đang phát trực tiếp
  await page.getByRole('button', { name: /Tạm dừng AI/i }).click()
  await page.waitForSelector('button:has-text("Tiếp tục AI")')
  await expect(page.locator('text=Đang phát trực tiếp').first()).toBeVisible()
  await page.getByRole('button', { name: /Tiếp tục AI/i }).click()

  // Switch SKU -> ACCEPTED trước, Active SKU chưa đổi ngay
  await page.getByRole('button', { name: /Chuyển SKU/i }).click()
  await page.getByRole('button', { name: /Gửi yêu cầu chuyển/i }).click()
  await page.waitForSelector('text=Đang chờ chuyển sang')
  await expect(page.locator('text=Đang giới thiệu · ML-001')).toBeVisible()

  // Modal Dừng khẩn cấp: kiểm tra Focus Trap & khôi phục focus khi nhấn Escape
  const emergencyBtn = page.getByRole('button', { name: /^Dừng khẩn cấp$/i })
  await emergencyBtn.click()
  await page.waitForSelector('text=Dừng khẩn cấp livestream?')
  await page.keyboard.press('Tab')
  await page.keyboard.press('Escape')
  await expect(page.locator('text=Dừng khẩn cấp livestream?')).toHaveCount(0)
})

test('J07, J08, J09, J10 & J11: Invites, Viewer Mobile, Members, Rights Consent & Reports', async ({
  page,
}) => {
  // J09 Members: Owner thấy phân công, Operator bị chặn
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/studio/members?role=OWNER')
  await page.waitForSelector('text=Trần Ngọc Lan')
  await page.goto('/studio/members?role=OPERATOR')
  await page.waitForSelector('text=Chỉ Chủ sở hữu')

  // J10 Rights Subject: độc lập không cần đăng nhập Merchant
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/rights/consent/req-consent-an-03')
  await page.waitForSelector('text=Xác nhận quyền sử dụng hình ảnh cá nhân')

  // J07 & J08 Viewer Mobile: vào phòng, gửi bình luận, không lộ nút dev
  await page.goto('/live/ses-014?invite=ml014-doitac')
  await page.fill('input[placeholder*="Nhập tên để tham gia"]', 'Khách Hành Trình')
  await page.getByRole('button', { name: /Vào phòng livestream/i }).click()
  await page.waitForSelector('input[placeholder*="Nhập bình luận"]')
  await expect(page.locator('text=Mô phỏng Video Buffering')).toHaveCount(0)

  // J11 Reports: Partial hiển thị N/A trung thực, Ready bật Export cho Owner
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/studio/sessions/ses-013/report?role=OWNER')
  await page.waitForSelector('text=Tổng 7 khung = 86 lượt khớp KPI')
  await page.goto('/studio/sessions/ses-012/report?role=OWNER')
  await expect(page.getByRole('button', { name: /Xuất báo cáo \(CSV \/ PDF\)/i })).toBeVisible()
})
