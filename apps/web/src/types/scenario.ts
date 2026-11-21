export type MockScenarioKey =
  | 'happy-path'
  | 'empty'
  | 'loading'
  | 'error'
  | 'permission-denied'
  | 'session-live'
  | 'ai-paused'
  | 'media-degraded'
  | 'command-conflict'
  | 'rights-revoked'
  | 'verification-pending'
  | 'report-partial'
  | 'invite-expired'

export interface MockScenarioOption {
  key: MockScenarioKey
  label: string
  group: 'Cơ bản' | 'Vận hành Live' | 'Cảnh báo & Ngoại lệ'
  description: string
}

export const MOCK_SCENARIO_OPTIONS: MockScenarioOption[] = [
  {
    key: 'happy-path',
    label: 'Mặc định (Đang phát + Tác vụ)',
    group: 'Cơ bản',
    description: 'Phiên #014 đang LIVE ổn định, có 3 việc cần xử lý và tài nguyên sẵn sàng.',
  },
  {
    key: 'empty',
    label: 'Workspace mới (Trống)',
    group: 'Cơ bản',
    description: 'Chưa có Presenter, sản phẩm hay phiên nào — hiển thị hướng dẫn bắt đầu.',
  },
  {
    key: 'loading',
    label: 'Đang tải (Skeleton)',
    group: 'Cơ bản',
    description: 'Mô phỏng trạng thái đang tải dữ liệu từ hệ thống.',
  },
  {
    key: 'error',
    label: 'Lỗi kết nối API',
    group: 'Cơ bản',
    description: 'Mô phỏng lỗi tải snapshot kèm nút thử lại an toàn.',
  },
  {
    key: 'permission-denied',
    label: 'Không có quyền truy cập',
    group: 'Cơ bản',
    description: 'Mô phỏng phiên/tài nguyên ngoài phạm vi phân công.',
  },
  {
    key: 'session-live',
    label: 'Phiên LIVE ổn định',
    group: 'Vận hành Live',
    description: 'Phiên #014 đang phát, AI đang hoạt động, Media ổn định.',
  },
  {
    key: 'ai-paused',
    label: 'LIVE + AI tạm dừng',
    group: 'Vận hành Live',
    description: 'Stream vẫn đang phát cảnh an toàn nhưng AI đang tạm dừng.',
  },
  {
    key: 'media-degraded',
    label: 'Media suy giảm (Fallback)',
    group: 'Cảnh báo & Ngoại lệ',
    description: 'Chất lượng hình ảnh giảm, đang dùng cảnh sản phẩm dự phòng.',
  },
  {
    key: 'command-conflict',
    label: 'Xung đột lệnh Operator',
    group: 'Cảnh báo & Ngoại lệ',
    description: 'Hai Operator gửi lệnh song song gây lệch phiên bản trạng thái.',
  },
  {
    key: 'rights-revoked',
    label: 'Thu hồi quyền Presenter',
    group: 'Cảnh báo & Ngoại lệ',
    description: 'Chủ thể quyền vừa thu hồi consent, khóa sử dụng Presenter liên quan.',
  },
  {
    key: 'verification-pending',
    label: 'Chờ xác minh OCOP',
    group: 'Cảnh báo & Ngoại lệ',
    description: 'Tri thức đã duyệt nhưng SKU còn thiếu chứng cứ OCOP, chặn Start.',
  },
  {
    key: 'report-partial',
    label: 'Báo cáo thiếu dữ liệu (Partial)',
    group: 'Cảnh báo & Ngoại lệ',
    description: 'Phiên đã kết thúc, một số chỉ số đang chờ tổng hợp hoặc N/A.',
  },
  {
    key: 'invite-expired',
    label: 'Lời mời xem live hết hạn',
    group: 'Cảnh báo & Ngoại lệ',
    description: 'Liên kết mời chính đã hết hạn, cần tạo liên kết mới.',
  },
]
