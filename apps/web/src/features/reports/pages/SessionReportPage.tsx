import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock,
  Download,
  FileSpreadsheet,
  FileText,
  Info,
  Loader2,
  Lock,
  MessageSquare,
  Radio,
  ShieldAlert,
} from 'lucide-react'
import { useScenario } from '@/hooks/useScenario'
import { useSessionReport } from '../hooks/useReports'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Banner } from '@/components/ui/Banner'
import { Button, ButtonLink } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import {
  buildSanitizedAuditCsv,
  buildSummaryPdfBlob,
  triggerBrowserDownload,
} from '@/lib/export-utils'
import { formatShortTime } from '@/lib/format'
import type { BadgeTone } from '@/lib/status-copy'
import type { ReportMetricValue, ReportTimelineSegment } from '@/types/m03'

type ReportTab = 'AI_COMMENTS' | 'MEDIA_STABILITY' | 'AUDIT_LOG'
type ExportJobState = 'IDLE' | 'EXPORT_REQUESTED' | 'PROCESSING' | 'READY'
type ExportFormat = 'CSV' | 'PDF'

const METRIC_STATUS_BADGE: Record<
  ReportMetricValue['status'],
  { label: string; tone: BadgeTone }
> = {
  MEASURED: { label: 'Đã đo', tone: 'success' },
  PARTIAL: { label: 'Một phần', tone: 'warning' },
  NOT_AVAILABLE: { label: 'N/A', tone: 'neutral' },
}

const TIMELINE_TONE: Record<
  ReportTimelineSegment['kind'],
  { dot: string; badge: BadgeTone; label: string }
> = {
  LIVE: { dot: 'bg-[var(--status-success)]', badge: 'success', label: 'Phát trực tiếp' },
  AI_PAUSED: { dot: 'bg-[var(--status-warning)]', badge: 'warning', label: 'AI tạm dừng' },
  MEDIA_DEGRADED: { dot: 'bg-[var(--status-warning)]', badge: 'warning', label: 'Media suy giảm' },
  STOPPED: { dot: 'bg-[var(--text-muted)]', badge: 'neutral', label: 'Đã kết thúc' },
  EMERGENCY: { dot: 'bg-[var(--status-danger)]', badge: 'danger', label: 'Dừng khẩn cấp' },
}

export function SessionReportPage() {
  const { id } = useParams<{ id: string }>()
  const { role } = useScenario()
  const { data: report, isLoading, isError, error, refetch } = useSessionReport(id)

  const [activeTab, setActiveTab] = useState<ReportTab>('AI_COMMENTS')
  const [exportOpen, setExportOpen] = useState(false)
  const [exportFormat, setExportFormat] = useState<ExportFormat>('CSV')
  const [exportState, setExportState] = useState<ExportJobState>('IDLE')
  const [exportMessage, setExportMessage] = useState<string | null>(null)

  useEffect(() => {
    if (exportState === 'EXPORT_REQUESTED') {
      const t = window.setTimeout(() => setExportState('PROCESSING'), 280)
      return () => window.clearTimeout(t)
    }
    if (exportState === 'PROCESSING') {
      const t = window.setTimeout(() => setExportState('READY'), 450)
      return () => window.clearTimeout(t)
    }
  }, [exportState])

  const handleStartExport = (fmt: ExportFormat) => {
    setExportFormat(fmt)
    setExportMessage(null)
    setExportState('EXPORT_REQUESTED')
  }

  const handleDownloadReadyFile = () => {
    if (!report) return
    if (exportFormat === 'CSV') {
      const csv = buildSanitizedAuditCsv(report)
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
      triggerBrowserDownload(blob, `${report.sessionCode}-audit-log-sanitized.csv`)
      setExportMessage(
        `Đã tải xuống ${report.sessionCode}-audit-log-sanitized.csv (đã vô hiệu hóa công thức bảng tính =, +, -, @).`,
      )
    } else {
      const blob = buildSummaryPdfBlob(report)
      triggerBrowserDownload(blob, `${report.sessionCode}-summary-report.pdf`)
      setExportMessage(`Đã tải xuống ${report.sessionCode}-summary-report.pdf (PDF 1.4 chuẩn).`)
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-20 rounded-[var(--radius-card)]" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-[var(--radius-card)]" />
          ))}
        </div>
        <Skeleton className="h-72 rounded-[var(--radius-card)]" />
      </div>
    )
  }

  if (isError || !report) {
    const errMsg = error instanceof Error ? error.message : 'Không thể tải báo cáo phiên.'
    return (
      <div className="space-y-4">
        <Link
          to="/studio/reports"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
        >
          <ArrowLeft className="h-4 w-4" />
          Quay lại lịch sử báo cáo
        </Link>
        <EmptyState
          tone="warning"
          icon={<Lock className="h-6 w-6" />}
          title="Không thể truy cập báo cáo phiên"
          description={errMsg}
          action={
            <Button variant="secondary" size="sm" onClick={() => refetch()}>
              Thử lại
            </Button>
          }
        />
      </div>
    )
  }

  const maxAdmissions = Math.max(1, ...report.intervalChart.map((p) => p.admissions))
  const maxConcurrent = Math.max(
    1,
    ...report.intervalChart.map((p) => p.concurrentViewers ?? 0),
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-sm">
        <Link
          to="/studio/reports"
          className="inline-flex min-h-9 items-center gap-1.5 rounded-[8px] px-2 py-1.5 font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)]"
        >
          <ArrowLeft className="h-4 w-4" />
          Báo cáo phiên
        </Link>
        <span className="text-[var(--text-muted)]">/</span>
        <span className="font-mono font-semibold text-[var(--text-primary)]">
          {report.sessionCode}
        </span>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Báo cáo: {report.sessionTitle}
          </h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Mã phiên {report.sessionCode}
            {report.startedAt ? ` · Bắt đầu ${formatShortTime(report.startedAt)}` : ' · Chưa bắt đầu'}
            {report.stoppedAt ? ` · Kết thúc ${formatShortTime(report.stoppedAt)}` : ''}
            {` · Cập nhật ${formatShortTime(report.generatedAt)}`}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge
            tone={
              report.reportStatus === 'READY'
                ? 'success'
                : report.reportStatus === 'PARTIAL'
                  ? 'warning'
                  : 'neutral'
            }
            label={
              report.reportStatus === 'READY'
                ? 'Báo cáo hoàn chỉnh (READY)'
                : report.reportStatus === 'PARTIAL'
                  ? 'Dữ liệu một phần (PARTIAL)'
                  : 'Đang tổng hợp (PENDING)'
            }
          />

          {report.lifecycle === 'LIVE' && (
            <ButtonLink
              to={`/studio/sessions/${report.sessionId}/control`}
              variant="secondary"
              size="sm"
              leftIcon={<Radio className="h-4 w-4 text-[var(--status-danger-fg)]" />}
            >
              Mở phòng điều khiển
            </ButtonLink>
          )}

          {report.canExport ? (
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                setExportState('IDLE')
                setExportMessage(null)
                setExportOpen(true)
              }}
            >
              <Download className="h-4 w-4" />
              Xuất báo cáo (CSV / PDF)
            </Button>
          ) : null}
        </div>
      </div>

      {report.isReducedOperatorView && (
        <Banner
          severity="info"
          title="Chế độ xem rút gọn dành cho Vận hành viên"
          description="Vận hành viên được xem chỉ số vận hành và dòng thời gian của phiên được phân công. Quyền xuất tệp CSV/PDF kiểm toán chỉ dành cho Chủ sở hữu không gian làm việc."
        />
      )}

      {report.reportStatus !== 'READY' && (
        <Card className="border-[var(--status-warning-border)] bg-[var(--status-warning-bg)]/45 p-4">
          <div className="flex items-start gap-3">
            <Info className="mt-0.5 h-5 w-5 shrink-0 text-[var(--status-warning-fg)]" />
            <div className="text-sm text-[var(--text-secondary)]">
              <p className="font-semibold text-[var(--text-primary)]">
                {report.reportStatus === 'PARTIAL'
                  ? 'Báo cáo đang thiếu một số chỉ số — hiển thị trung thực theo dữ liệu đã đo'
                  : 'Báo cáo đang được tổng hợp — hiển thị trung thực theo dữ liệu đã đo'}
              </p>
              <p className="mt-0.5">
                Các chỉ số chưa đủ dữ liệu xác thực sẽ hiển thị <strong>N/A</strong> kèm lý do,
                không tự điền số 0 giả hoặc suy diễn trước khi có xác nhận từ hệ thống.
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* 5 thẻ KPI có nguồn đo, chống vỡ dòng badge & dùng số căn thẳng tabular-nums */}
      <section aria-label="Chỉ số tổng quan phiên livestream" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {report.kpis.map((kpi) => {
          const st = METRIC_STATUS_BADGE[kpi.status]
          return (
            <Card key={kpi.key} className="flex flex-col justify-between p-4">
              <div className="flex items-start justify-between gap-2">
                <span className="text-xs font-semibold leading-snug text-[var(--text-secondary)]">
                  {kpi.label}
                </span>
                <StatusBadge tone={st.tone} label={st.label} showIcon={false} subtle={kpi.status === 'MEASURED'} />
              </div>
              <div className="mt-3">
                <p className="text-2xl font-bold tracking-tight tabular-nums text-[var(--text-primary)]">
                  {kpi.value === null ? (
                    <span className="text-[var(--text-muted)]">N/A</span>
                  ) : (
                    <>
                      {kpi.value}
                      {kpi.unit ? (
                        <span className="ml-1 text-xs font-medium text-[var(--text-secondary)]">
                          {kpi.unit}
                        </span>
                      ) : null}
                    </>
                  )}
                </p>
                <p className="mt-1.5 text-[11px] text-[var(--text-muted)]">
                  Nguồn: {kpi.source}
                </p>
                {kpi.reason ? (
                  <p className="mt-1 text-[11px] text-[var(--status-warning-fg)]">{kpi.reason}</p>
                ) : null}
              </div>
            </Card>
          )
        })}
      </section>

      {/* Biểu đồ lượt vào & Dòng thời gian trạng thái */}
      <div className="grid gap-6 lg:grid-cols-12">
        <Card className="p-5 lg:col-span-7 space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-base font-bold text-[var(--text-primary)]">
                Lượt vào phòng theo khung thời gian
              </h2>
              <p className="text-xs text-[var(--text-secondary)]">
                {report.chartCoverageLabel} · Phân biệt với Người xem đồng thời
              </p>
            </div>
            <StatusBadge tone="info" label="Theo khung 15 phút" showIcon={false} subtle />
          </div>

          {report.intervalChart.length === 0 ? (
            <div className="rounded-[var(--radius-input)] border border-dashed border-[var(--border-default)] bg-[var(--bg-subtle)] p-6 text-center text-xs text-[var(--text-muted)]">
              Chưa có dữ liệu biểu đồ vì phiên chưa phát trực tiếp.
            </div>
          ) : (
            <div className="w-full overflow-x-auto">
              <svg
                viewBox="0 0 560 200"
                className="h-48 w-full min-w-[360px]"
                role="img"
                aria-label="Biểu đồ lượt vào phòng theo khung thời gian"
              >
                {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
                  const y = 165 - ratio * 135
                  return (
                    <line
                      key={ratio}
                      x1="36"
                      y1={y}
                      x2="544"
                      y2={y}
                      stroke="currentColor"
                      strokeOpacity="0.12"
                      strokeDasharray="3 3"
                    />
                  )
                })}
                {report.intervalChart.map((pt, idx) => {
                  const slotWidth = 500 / Math.max(1, report.intervalChart.length)
                  const barWidth = Math.min(44, slotWidth * 0.55)
                  const x = 44 + idx * slotWidth + (slotWidth - barWidth) / 2
                  const h = (pt.admissions / maxAdmissions) * 130
                  const y = 165 - h
                  return (
                    <g key={pt.bucketLabel}>
                      <rect
                        x={x}
                        y={y}
                        width={barWidth}
                        height={Math.max(4, h)}
                        rx="6"
                        fill="#F5C430"
                      />
                      <text
                        x={x + barWidth / 2}
                        y={Math.max(18, y - 6)}
                        textAnchor="middle"
                        fontSize="11"
                        fontWeight="600"
                        fill="currentColor"
                      >
                        {pt.admissions}
                      </text>
                      <text
                        x={x + barWidth / 2}
                        y="186"
                        textAnchor="middle"
                        fontSize="10"
                        fill="currentColor"
                        opacity="0.7"
                      >
                        {pt.bucketLabel}
                      </text>
                    </g>
                  )
                })}
              </svg>
            </div>
          )}

          {/* Biểu đồ người xem đồng thời (tùy chọn khi có dữ liệu telemetry) */}
          <div className="border-t border-[var(--border-default)] pt-4">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                Người xem đồng thời (tùy chọn theo telemetry)
              </h3>
              <StatusBadge
                tone={report.hasConcurrentTelemetry ? 'success' : 'neutral'}
                label={report.hasConcurrentTelemetry ? 'Có dữ liệu đo' : 'N/A · Chưa có dữ liệu'}
                subtle={!report.hasConcurrentTelemetry}
              />
            </div>
            {report.hasConcurrentTelemetry ? (
              <svg
                viewBox="0 0 560 110"
                className="mt-2 h-28 w-full min-w-[360px]"
                role="img"
                aria-label="Biểu đồ người xem đồng thời"
              >
                <polyline
                  fill="none"
                  stroke="#0EA5E9"
                  strokeWidth="2.5"
                  points={report.intervalChart
                    .map((pt, idx) => {
                      const slotWidth = 500 / Math.max(1, report.intervalChart.length)
                      const x = 44 + idx * slotWidth + slotWidth / 2
                      const v = pt.concurrentViewers ?? 0
                      const y = 85 - (v / maxConcurrent) * 65
                      return `${x},${y}`
                    })
                    .join(' ')}
                />
                {report.intervalChart.map((pt, idx) => {
                  const slotWidth = 500 / Math.max(1, report.intervalChart.length)
                  const x = 44 + idx * slotWidth + slotWidth / 2
                  const v = pt.concurrentViewers ?? 0
                  const y = 85 - (v / maxConcurrent) * 65
                  return (
                    <g key={`cv-${pt.bucketLabel}`}>
                      <circle cx={x} cy={y} r="4" fill="#0EA5E9" />
                      <text
                        x={x}
                        y={y - 8}
                        textAnchor="middle"
                        fontSize="10"
                        fill="currentColor"
                      >
                        {v}
                      </text>
                    </g>
                  )
                })}
              </svg>
            ) : (
              <p className="mt-2 text-xs text-[var(--text-muted)]">
                Phiên chưa có dữ liệu đo người xem đồng thời từ media telemetry. Chỉ hiển thị biểu đồ
                lượt vào phòng đã xác thực.
              </p>
            )}
          </div>
        </Card>

        {/* State Timeline */}
        <Card className="p-5 lg:col-span-5">
          <div className="flex items-center justify-between gap-2">
            <div>
              <h2 className="text-base font-bold text-[var(--text-primary)]">
                Dòng thời gian trạng thái phiên
              </h2>
              <p className="text-xs text-[var(--text-secondary)]">
                Tách biệt LIVE, AI tạm dừng, Media suy giảm và Kết thúc
              </p>
            </div>
            <Clock className="h-4 w-4 text-[var(--text-muted)]" />
          </div>

          <ol className="mt-4 space-y-4">
            {report.timeline.map((seg) => {
              const tone = TIMELINE_TONE[seg.kind]
              return (
                <li key={seg.id} className="relative flex gap-3 pl-1">
                  <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${tone.dot}`} />
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-sm font-semibold text-[var(--text-primary)]">
                        {seg.title}
                      </span>
                      <span className="font-mono text-xs text-[var(--text-muted)]">
                        {seg.timeLabel}
                      </span>
                    </div>
                    <p className="text-xs text-[var(--text-secondary)]">{seg.detail}</p>
                    <StatusBadge tone={tone.badge} label={tone.label} />
                  </div>
                </li>
              )
            })}
          </ol>
        </Card>
      </div>

      {/* 3 Tab chi tiết dùng đúng biến token của hệ thống thiết kế */}
      <Card className="overflow-hidden">
        <div
          role="tablist"
          aria-label="Chi tiết báo cáo phiên"
          className="flex flex-wrap border-b border-[var(--border-default)] bg-[var(--bg-subtle)] px-4 pt-2"
        >
          {(
            [
              { id: 'AI_COMMENTS', label: 'AI & Bình luận', icon: MessageSquare },
              { id: 'MEDIA_STABILITY', label: 'Media & Độ ổn định', icon: Activity },
              { id: 'AUDIT_LOG', label: 'Nhật ký hoạt động', icon: FileText },
            ] as const
          ).map((tab) => {
            const Icon = tab.icon
            const active = activeTab === tab.id
            return (
              <button
                key={tab.id}
                role="tab"
                type="button"
                aria-selected={active}
                onClick={() => setActiveTab(tab.id)}
                className={`inline-flex min-h-10 items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-semibold transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)] ${
                  active
                    ? 'border-[var(--brand-amber)] text-[var(--text-primary)]'
                    : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            )
          })}
        </div>

        <div className="p-5">
          {activeTab === 'AI_COMMENTS' && (
            <div className="space-y-4">
              <div className="rounded-[var(--radius-input)] border border-[var(--border-default)] bg-[var(--bg-subtle)] p-3.5 text-xs text-[var(--text-secondary)]">
                <strong className="text-[var(--text-primary)]">Nguyên tắc đếm câu AI đã phát:</strong>{' '}
                Chỉ tính các lượt phát nhận được xác nhận{' '}
                <code className="font-mono font-semibold">PlaybackCompleted ACK</code> duy nhất
                (đã khử trùng lặp). Hoàn tất tổng hợp giọng nói (TTS) không đồng nghĩa đã phát tới
                khách xem.
              </div>

              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                {[
                  { label: 'Bình luận đã nhận', value: report.aiFunnel.commentsReceived },
                  { label: 'Đủ điều kiện phản hồi', value: report.aiFunnel.commentsEligible },
                  { label: 'Lượt AI chuẩn bị', value: report.aiFunnel.turnsPrepared },
                  { label: 'Lượt đã bắt đầu phát', value: report.aiFunnel.turnsCommitted },
                  {
                    label: 'Đã phát xong tới người xem',
                    value: report.aiFunnel.turnsPlayedAck,
                    highlight: true,
                  },
                ].map((step) => (
                  <div
                    key={step.label}
                    className={`rounded-[var(--radius-input)] border p-3.5 ${
                      step.highlight
                        ? 'border-[var(--brand-amber)] bg-[var(--brand-amber)]/10'
                        : 'border-[var(--border-default)] bg-[var(--bg-surface)]'
                    }`}
                  >
                    <p className="text-xs text-[var(--text-secondary)]">{step.label}</p>
                    <p className="mt-1 text-2xl font-bold tabular-nums text-[var(--text-primary)]">
                      {step.value}
                    </p>
                  </div>
                ))}
              </div>
              <p className="text-xs text-[var(--text-muted)]">
                Số tín hiệu xác nhận trùng lặp đã được loại bỏ tự động:{' '}
                <strong className="tabular-nums text-[var(--text-primary)]">
                  {report.aiFunnel.dedupedAckCount}
                </strong>
              </p>
            </div>
          )}

          {activeTab === 'MEDIA_STABILITY' && (
            <div className="space-y-3">
              {report.mediaIncidents.length === 0 ? (
                <div className="flex items-center gap-2 rounded-[var(--radius-input)] border border-[var(--status-success-border)] bg-[var(--status-success-bg)] p-4 text-sm text-[var(--status-success-fg)]">
                  <CheckCircle2 className="h-5 w-5 shrink-0" />
                  Không ghi nhận sự cố suy giảm media hoặc chuyển cảnh dự phòng trong phiên này.
                </div>
              ) : (
                report.mediaIncidents.map((inc) => (
                  <div
                    key={inc.id}
                    className="flex flex-col gap-2 rounded-[var(--radius-input)] border border-[var(--border-default)] p-4 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="flex items-start gap-3">
                      <AlertTriangle
                        className={`mt-0.5 h-5 w-5 shrink-0 ${
                          inc.severity === 'danger'
                            ? 'text-[var(--status-danger-fg)]'
                            : 'text-[var(--status-warning-fg)]'
                        }`}
                      />
                      <div>
                        <p className="text-sm font-semibold text-[var(--text-primary)]">
                          {inc.summary}
                        </p>
                        <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                          Chế độ dự phòng: {inc.fallbackUsed}
                        </p>
                      </div>
                    </div>
                    <StatusBadge tone={inc.severity} label={inc.timeLabel} />
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'AUDIT_LOG' && (
            <div className="space-y-3">
              {role === 'OPERATOR' && (
                <p className="text-xs text-[var(--text-muted)]">
                  Đang hiển thị nhật ký vận hành rút gọn. Chủ sở hữu có thể xuất tệp CSV đầy đủ.
                </p>
              )}
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] border-collapse text-left text-xs">
                  <thead>
                    <tr className="border-b border-[var(--border-default)] text-[var(--text-muted)]">
                      <th className="py-2.5 pr-4 font-semibold">Thời điểm</th>
                      <th className="py-2.5 pr-4 font-semibold">Người thực hiện</th>
                      <th className="py-2.5 pr-4 font-semibold">Hành động</th>
                      <th className="py-2.5 pr-4 font-semibold">Kết quả</th>
                      <th className="py-2.5 font-semibold">Lý do / Ghi chú</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border-default)]">
                    {report.auditEvents.map((ev) => (
                      <tr key={ev.id}>
                        <td className="py-2.5 pr-4 font-mono text-[var(--text-muted)] whitespace-nowrap">
                          {formatShortTime(ev.occurredAt)}
                        </td>
                        <td className="py-2.5 pr-4 font-medium text-[var(--text-primary)] whitespace-nowrap">
                          {ev.actorName}
                        </td>
                        <td className="py-2.5 pr-4 font-mono font-semibold text-[var(--text-primary)] whitespace-nowrap">
                          {ev.action}
                        </td>
                        <td className="py-2.5 pr-4 whitespace-nowrap">
                          <StatusBadge
                            tone={ev.decision === 'APPLIED' ? 'success' : 'danger'}
                            label={ev.decision}
                          />
                        </td>
                        <td className="py-2.5 text-[var(--text-secondary)]">{ev.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Owner Async Export Modal */}
      <Modal
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        title="Xuất báo cáo phiên livestream (Chủ sở hữu)"
      >
        <div className="space-y-4">
          <p className="text-sm text-[var(--text-secondary)]">
            Chọn định dạng xuất bất đồng bộ. Tệp CSV kiểm toán tự động vô hiệu hóa ký tự mở đầu công
            thức bảng tính (<code className="font-mono">=, +, -, @</code>) để tránh CSV Formula
            Injection.
          </p>

          <div className="grid gap-3 sm:grid-cols-2">
            <button
              type="button"
              onClick={() => handleStartExport('CSV')}
              className={`flex items-start gap-3 rounded-[var(--radius-input)] border p-3.5 text-left transition-colors cursor-pointer ${
                exportFormat === 'CSV' && exportState !== 'IDLE'
                  ? 'border-[var(--brand-amber)] bg-[var(--brand-amber)]/10'
                  : 'border-[var(--border-default)] hover:bg-[var(--bg-subtle)]'
              }`}
            >
              <FileSpreadsheet className="mt-0.5 h-5 w-5 shrink-0 text-[var(--status-success-fg)]" />
              <div>
                <p className="text-sm font-semibold text-[var(--text-primary)]">
                  Nhật ký kiểm toán (CSV)
                </p>
                <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                  UTF-8 BOM, đã lọc an toàn công thức
                </p>
              </div>
            </button>

            <button
              type="button"
              onClick={() => handleStartExport('PDF')}
              className={`flex items-start gap-3 rounded-[var(--radius-input)] border p-3.5 text-left transition-colors cursor-pointer ${
                exportFormat === 'PDF' && exportState !== 'IDLE'
                  ? 'border-[var(--brand-amber)] bg-[var(--brand-amber)]/10'
                  : 'border-[var(--border-default)] hover:bg-[var(--bg-subtle)]'
              }`}
            >
              <FileText className="mt-0.5 h-5 w-5 shrink-0 text-[var(--status-danger-fg)]" />
              <div>
                <p className="text-sm font-semibold text-[var(--text-primary)]">
                  Báo cáo tổng hợp (PDF)
                </p>
                <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                  Tài liệu PDF 1.4 kèm chỉ số & xác nhận phát
                </p>
              </div>
            </button>
          </div>

          {exportState !== 'IDLE' && (
            <div className="rounded-[var(--radius-input)] border border-[var(--border-default)] bg-[var(--bg-subtle)] p-4 space-y-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">
                  Trạng thái tác vụ xuất ({exportFormat})
                </span>
                <StatusBadge
                  tone={
                    exportState === 'READY'
                      ? 'success'
                      : exportState === 'PROCESSING'
                        ? 'info'
                        : 'warning'
                  }
                  label={exportState}
                />
              </div>

              {exportState === 'READY' ? (
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <p className="text-xs text-[var(--text-secondary)]">
                    Tệp đã sẵn sàng để tải xuống trình duyệt.
                  </p>
                  <Button variant="primary" size="sm" onClick={handleDownloadReadyFile}>
                    <Download className="h-4 w-4" />
                    Tải tệp {exportFormat}
                  </Button>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
                  <Loader2 className="h-4 w-4 animate-spin text-[var(--brand-amber)]" />
                  {exportState === 'EXPORT_REQUESTED'
                    ? 'Đang khởi tạo yêu cầu xuất báo cáo...'
                    : 'Đang đóng gói dữ liệu và kiểm tra an toàn định dạng...'}
                </div>
              )}

              {exportMessage && (
                <p className="flex items-center gap-1.5 text-xs font-medium text-[var(--status-success-fg)]">
                  <CheckCircle2 className="h-4 w-4 shrink-0" />
                  {exportMessage}
                </p>
              )}
            </div>
          )}

          <div className="flex items-center justify-between border-t border-[var(--border-default)] pt-3">
            <span className="inline-flex items-center gap-1 text-[11px] text-[var(--text-muted)]">
              <ShieldAlert className="h-3.5 w-3.5" />
              Mock Export · Tải tệp thật trên trình duyệt
            </span>
            <Button variant="ghost" size="sm" onClick={() => setExportOpen(false)}>
              Đóng
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
