import type { UserRole } from '@/types/auth'
import type { MockScenarioKey } from '@/types/scenario'
import type {
  DashboardActionItem,
  DashboardAssetCardItem,
  DashboardSnapshot,
} from '@/features/dashboard/types/dashboard.types'
import {
  SESSION_LIVE_014,
  SESSION_PREPARING_015,
  SESSION_STOPPED_012,
  SESSION_STOPPED_013,
} from '@/mocks/fixtures/catalog.fixtures'
import { WORKSPACE_PRIMARY } from '@/mocks/fixtures/workspace.fixtures'

const BASE_ASSET_CARDS: DashboardAssetCardItem[] = [
  {
    id: 'presenter',
    label: 'AI Presenter',
    count: 2,
    subtitle: '1 hợp lệ · 1 đang tạo',
    statusLabel: 'Sẵn sàng chọn',
    statusTone: 'success',
    targetRoute: '/studio/presenters',
  },
  {
    id: 'products',
    label: 'Sản phẩm & OCOP',
    count: 5,
    subtitle: '3 đủ điều kiện · 2 chờ OCOP',
    statusLabel: '3 đã xác minh',
    statusTone: 'info',
    targetRoute: '/studio/products',
  },
  {
    id: 'knowledge',
    label: 'Tri thức & Claims',
    count: 8,
    subtitle: 'Bản đã duyệt có nguồn',
    statusLabel: 'Đã kiểm chứng',
    statusTone: 'success',
    targetRoute: '/studio/knowledge',
  },
  {
    id: 'sessions',
    label: 'Phiên đã tạo',
    count: 4,
    subtitle: '1 đang livestream',
    statusLabel: 'Đang vận hành',
    statusTone: 'warning',
    targetRoute: '/studio/sessions',
  },
]

const EMPTY_ASSET_CARDS: DashboardAssetCardItem[] = [
  {
    id: 'presenter',
    label: 'AI Presenter',
    count: 0,
    subtitle: 'Chưa tạo người dẫn AI',
    statusLabel: 'Chưa thiết lập',
    statusTone: 'neutral',
    targetRoute: '/studio/presenters',
  },
  {
    id: 'products',
    label: 'Sản phẩm & OCOP',
    count: 0,
    subtitle: 'Chưa có hồ sơ sản phẩm',
    statusLabel: 'Chưa thiết lập',
    statusTone: 'neutral',
    targetRoute: '/studio/products',
  },
  {
    id: 'knowledge',
    label: 'Tri thức & Claims',
    count: 0,
    subtitle: 'Chưa có tài liệu duyệt',
    statusLabel: 'Chưa thiết lập',
    statusTone: 'neutral',
    targetRoute: '/studio/knowledge',
  },
  {
    id: 'sessions',
    label: 'Phiên đã tạo',
    count: 0,
    subtitle: 'Chưa có phiên livestream',
    statusLabel: 'Sẵn sàng tạo',
    statusTone: 'neutral',
    targetRoute: '/studio/sessions',
  },
]

const OWNER_DEFAULT_ACTIONS: DashboardActionItem[] = [
  {
    id: 'act-story-01',
    priority: 'APPROVAL',
    title: 'Kịch bản giới thiệu Mứt Mận Mường Lát',
    resourceLabel: 'Phiên #015 · Bản sửa v2',
    statusLabel: 'Cần phê duyệt',
    statusTone: 'warning',
    targetRoute: '/studio/sessions/ses-015/story',
    actionableByViewer: true,
  },
  {
    id: 'act-ocop-02',
    priority: 'BLOCKER',
    title: 'Bổ sung chứng cứ OCOP cho Trà thảo mộc Sơn La',
    resourceLabel: 'SKU ML-003 · Hồ sơ OCOP',
    statusLabel: 'Đang chờ tài liệu',
    statusTone: 'warning',
    targetRoute: '/studio/products/sku-ml-003',
    actionableByViewer: true,
  },
  {
    id: 'act-presenter-03',
    priority: 'INFO',
    title: 'Presenter Mai · gói clip chuyển động',
    resourceLabel: 'Phong cách Chuyên nghiệp · v1',
    statusLabel: 'Đang tạo',
    statusTone: 'info',
    targetRoute: '/studio/presenters/prs-mai-02',
    actionableByViewer: true,
  },
]

const OPERATOR_DEFAULT_ACTIONS: DashboardActionItem[] = [
  {
    id: 'act-op-live-01',
    priority: 'SETUP',
    title: 'Giám sát hàng đợi bình luận Phiên #014',
    resourceLabel: 'Phiên được phân công · Đang phát',
    statusLabel: 'Đang hoạt động',
    statusTone: 'success',
    targetRoute: '/studio/sessions/ses-014/control',
    actionableByViewer: true,
  },
  {
    id: 'act-op-rev-02',
    priority: 'APPROVAL',
    title: 'Đề xuất cập nhật giá Mật ong rừng 500ml',
    resourceLabel: 'SKU ML-002 · Đề xuất của bạn',
    statusLabel: 'Đang chờ Chủ sở hữu',
    statusTone: 'warning',
    targetRoute: '/studio/knowledge',
    actionableByViewer: false,
    waitingRoleLabel: 'Chờ Chủ sở hữu duyệt',
  },
  {
    id: 'act-op-ocop-03',
    priority: 'SETUP',
    title: 'Tải thêm ảnh nhãn sản phẩm cho SKU ML-003',
    resourceLabel: 'Bản nháp sản phẩm · Có thể bổ sung',
    statusLabel: 'Cần bổ sung',
    statusTone: 'info',
    targetRoute: '/studio/products/sku-ml-003',
    actionableByViewer: true,
  },
]

export function buildDashboardSnapshot(
  scenario: MockScenarioKey,
  role: UserRole,
): DashboardSnapshot {
  const isOwner = role === 'OWNER'
  const recentForRole = isOwner
    ? [SESSION_LIVE_014, SESSION_PREPARING_015, SESSION_STOPPED_013]
    : [SESSION_LIVE_014, SESSION_STOPPED_013]

  const base: DashboardSnapshot = {
    workspaceName: WORKSPACE_PRIMARY.displayName,
    snapshotRevision: 42,
    generatedAt: '2026-11-21T08:15:00Z',
    freshness: 'CONNECTED',
    hero: isOwner
      ? {
          headline: 'Sẵn sàng cho phiên giới thiệu đặc sản',
          summary:
            'Bạn có 2 việc cần xử lý và Phiên #014 đang phát trực tiếp ổn định.',
          ctaLabel: 'Mở phòng điều khiển',
          targetRoute: '/studio/sessions/ses-014/control',
          secondaryLabel: 'Xem công việc',
          secondaryRoute: '#action-center',
        }
      : {
          headline: 'Phiên #014 đang phát trực tiếp',
          summary:
            'Bạn đang được phân công vận hành Phiên #014. Các đề xuất nội dung cần Chủ sở hữu phê duyệt.',
          ctaLabel: 'Mở phòng điều khiển',
          targetRoute: '/studio/sessions/ses-014/control',
        },
    criticalAlerts: [],
    actionItems: isOwner ? OWNER_DEFAULT_ACTIONS : OPERATOR_DEFAULT_ACTIONS,
    totalActionCount: isOwner ? 3 : 3,
    featuredSession: SESSION_LIVE_014,
    assetCards: BASE_ASSET_CARDS,
    recentSessions: recentForRole,
  }

  switch (scenario) {
    case 'empty':
      return {
        ...base,
        snapshotRevision: 1,
        hero: isOwner
          ? {
              headline: 'Bắt đầu thiết lập Merchant Studio',
              summary:
                'Tạo AI Presenter có xác nhận quyền và bổ sung 2–5 sản phẩm OCOP để mở phiên livestream đầu tiên.',
              ctaLabel: 'Tạo AI Presenter đầu tiên',
              targetRoute: '/studio/presenters',
              secondaryLabel: 'Thêm sản phẩm',
              secondaryRoute: '/studio/products',
            }
          : {
              headline: 'Chưa có phiên nào được phân công',
              summary:
                'Bạn đã là thành viên của workspace. Liên hệ Chủ sở hữu để được phân công vào phiên livestream.',
              ctaLabel: 'Xem sản phẩm được cấp quyền',
              targetRoute: '/studio/products',
            },
        actionItems: isOwner
          ? [
              {
                id: 'empty-1',
                priority: 'SETUP',
                title: 'Tạo AI Presenter và gửi yêu cầu xác nhận quyền',
                resourceLabel: 'Bước 1 · AI Presenter Studio',
                statusLabel: 'Chưa bắt đầu',
                statusTone: 'neutral',
                targetRoute: '/studio/presenters',
                actionableByViewer: true,
              },
              {
                id: 'empty-2',
                priority: 'SETUP',
                title: 'Tải hồ sơ 2–5 sản phẩm thực phẩm & OCOP',
                resourceLabel: 'Bước 2 · Sản phẩm & OCOP',
                statusLabel: 'Chưa bắt đầu',
                statusTone: 'neutral',
                targetRoute: '/studio/products',
                actionableByViewer: true,
              },
            ]
          : [],
        totalActionCount: isOwner ? 2 : 0,
        featuredSession: null,
        assetCards: EMPTY_ASSET_CARDS,
        recentSessions: [],
      }

    case 'ai-paused':
      return {
        ...base,
        hero: {
          headline: 'Phiên #014 vẫn đang LIVE · AI đang tạm dừng',
          summary:
            'Luồng phát sóng vẫn giữ cảnh an toàn cho người xem. Bạn có thể vào phòng điều khiển để kiểm tra và tiếp tục AI.',
          ctaLabel: 'Mở phòng điều khiển',
          targetRoute: '/studio/sessions/ses-014/control',
        },
        criticalAlerts: [
          {
            id: 'alert-ai-paused',
            severity: 'warning',
            title: 'AI đang tạm dừng trong Phiên #014',
            description:
              'Tạm dừng AI không làm tắt livestream. Hệ thống đang phát cảnh sản phẩm an toàn cho đến khi bạn chọn Tiếp tục AI.',
            actionLabel: 'Mở phòng điều khiển',
            targetRoute: '/studio/sessions/ses-014/control',
          },
        ],
        featuredSession: {
          ...SESSION_LIVE_014,
          aiState: 'PAUSED',
          mediaHealth: 'HEALTHY',
        },
      }

    case 'media-degraded':
      return {
        ...base,
        hero: {
          headline: 'Chất lượng hình ảnh Phiên #014 đang giảm',
          summary:
            'Luồng live vẫn hoạt động với cảnh sản phẩm dự phòng và âm thanh đã xác minh. Kiểm tra chẩn đoán trong phòng điều khiển.',
          ctaLabel: 'Mở chẩn đoán Media',
          targetRoute: '/studio/sessions/ses-014/control',
        },
        criticalAlerts: [
          {
            id: 'alert-media-degraded',
            severity: 'warning',
            title: 'Media suy giảm — Đang dùng cảnh sản phẩm dự phòng',
            description:
              'Luồng phát sóng vẫn đang LIVE. Âm thanh đã xác minh tiếp tục phát bình thường trong khi hệ thống phục hồi chuyển động.',
            actionLabel: 'Mở phòng điều khiển',
            targetRoute: '/studio/sessions/ses-014/control',
          },
        ],
        featuredSession: {
          ...SESSION_LIVE_014,
          mediaHealth: 'DEGRADED',
          fallbackDescription: 'Đang dùng cảnh sản phẩm dự phòng + âm thanh xác minh',
        },
      }

    case 'command-conflict':
      return {
        ...base,
        criticalAlerts: [
          {
            id: 'alert-conflict',
            severity: 'warning',
            title: 'Phát hiện xung đột lệnh vận hành tại Phiên #014',
            description:
              'Lệnh chuyển SKU của Trần Ngọc Lan trùng thời điểm với lệnh tạm dừng AI của Lê Thanh Bình. Hệ thống đã đồng bộ lại trạng thái mới nhất.',
            actionLabel: 'Xem nhật ký lệnh',
            targetRoute: '/studio/sessions/ses-014/control',
          },
        ],
        actionItems: [
          {
            id: 'act-conflict-01',
            priority: 'CRITICAL',
            title: 'Kiểm tra kết quả xung đột lệnh giữa 2 Vận hành viên',
            resourceLabel: 'Phiên #014 · Revision #43',
            statusLabel: 'Cần đối chiếu',
            statusTone: 'warning',
            targetRoute: '/studio/sessions/ses-014/control',
            actionableByViewer: true,
          },
          ...base.actionItems.slice(0, 2),
        ],
      }

    case 'rights-revoked':
      return {
        ...base,
        hero: {
          headline: 'Quyền sử dụng Presenter đã bị thu hồi',
          summary:
            'Chủ thể quyền vừa thu hồi đồng thuận cho Presenter Linh. Tài sản liên quan đã bị khóa sử dụng cho phiên mới.',
          ctaLabel: 'Kiểm tra quyền Presenter',
          targetRoute: '/studio/presenters',
        },
        criticalAlerts: [
          {
            id: 'alert-rights-revoked',
            severity: 'danger',
            title: 'Quyền hình ảnh của Presenter Linh đã bị thu hồi',
            description:
              'Hệ thống tự động khóa sử dụng các clip liên quan và vô hiệu hóa bản nháp chờ phát. Cần chọn Presenter hợp lệ khác.',
            actionLabel: 'Mở AI Presenter Studio',
            targetRoute: '/studio/presenters',
          },
        ],
        actionItems: [
          {
            id: 'act-rights-01',
            priority: 'CRITICAL',
            title: 'Thay thế AI Presenter cho Phiên #015 do thu hồi quyền',
            resourceLabel: 'Presenter Linh · Đã bị khóa',
            statusLabel: 'Bị chặn',
            statusTone: 'danger',
            targetRoute: '/studio/presenters',
            actionableByViewer: isOwner,
            waitingRoleLabel: isOwner ? undefined : 'Chờ Chủ sở hữu xử lý',
          },
          ...base.actionItems.slice(0, 2),
        ],
        assetCards: BASE_ASSET_CARDS.map((card) =>
          card.id === 'presenter'
            ? {
                ...card,
                subtitle: '1 bị thu hồi quyền · 1 đang tạo',
                statusLabel: 'Cần xử lý quyền',
                statusTone: 'danger',
              }
            : card,
        ),
      }

    case 'verification-pending':
      return {
        ...base,
        hero: isOwner
          ? {
              headline: 'Phiên #015 chưa đủ điều kiện khởi chạy',
              summary:
                'Tri thức sản phẩm đã duyệt nhưng 2 sản phẩm vẫn đang chờ xác minh OCOP độc lập. Cần bổ sung chứng cứ trước khi Start.',
              ctaLabel: 'Xem danh sách kiểm tra sẵn sàng',
              targetRoute: '/studio/sessions/ses-015/readiness',
            }
          : {
              headline: 'Phiên #015 đang chờ xác minh hồ sơ OCOP',
              summary:
                'Bạn có thể bổ sung tài liệu nháp cho sản phẩm ML-003. Chỉ Chủ sở hữu mới có quyền gửi xác minh và khởi chạy phiên.',
              ctaLabel: 'Bổ sung hồ sơ nháp',
              targetRoute: '/studio/products/sku-ml-003',
            },
        criticalAlerts: [
          {
            id: 'alert-ocop-pending',
            severity: 'info',
            title: 'Chưa thể khởi chạy Phiên #015 — Chờ xác minh OCOP',
            description:
              'Tri thức đã duyệt không thay thế xác minh OCOP. Vui lòng hoàn thiện chứng cứ cho SKU ML-003 và ML-005.',
            actionLabel: 'Mở Sản phẩm & OCOP',
            targetRoute: '/studio/products',
          },
        ],
        featuredSession: SESSION_PREPARING_015,
      }

    case 'report-partial':
      return {
        ...base,
        hero: {
          headline: 'Báo cáo Phiên #013 đang được tổng hợp một phần',
          summary:
            'Các chỉ số thời lượng và câu AI đã phát đã sẵn sàng. Số người xem đồng thời hiện chưa có dữ liệu đo và hiển thị rõ lý do.',
          ctaLabel: 'Mở báo cáo Phiên #013',
          targetRoute: '/studio/sessions/ses-013/report',
        },
        featuredSession: SESSION_STOPPED_013,
        recentSessions: isOwner
          ? [SESSION_STOPPED_013, SESSION_PREPARING_015, SESSION_STOPPED_012]
          : [SESSION_STOPPED_013],
      }

    case 'invite-expired':
      return {
        ...base,
        criticalAlerts: [
          {
            id: 'alert-invite-expired',
            severity: 'warning',
            title: 'Liên kết mời xem live “Đối tác” đã hết hạn',
            description:
              'Khách mới không thể tham gia bằng liên kết cũ. Chủ sở hữu cần tạo liên kết mời và mã QR mới cho Phiên #014.',
            actionLabel: isOwner ? 'Quản lý lời mời' : 'Xem trạng thái phiên',
            targetRoute: isOwner
              ? '/studio/sessions/ses-014/invites'
              : '/studio/sessions/ses-014/control',
          },
        ],
      }

    case 'session-live':
    case 'happy-path':
    default:
      return base
  }
}
