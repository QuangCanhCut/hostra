import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Lock, Plus, ShieldAlert } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Banner } from '@/components/ui/Banner'
import { Modal } from '@/components/ui/Modal'
import { Drawer } from '@/components/ui/Drawer'
import { EmptyState } from '@/components/ui/EmptyState'
import { Skeleton } from '@/components/ui/Skeleton'
import { useAuth } from '@/features/auth/hooks/useAuth'
import {
  useCreateInvite,
  useInvites,
  useRevokeInvite,
} from '@/features/invitations/hooks/useInvites'
import { QrCodePreview } from '@/features/invitations/components/QrCodePreview'
import type { ViewerInviteRecord } from '@/types/m03'
import { formatShortTime } from '@/lib/format'
import { cn } from '@/lib/cn'

export function InvitesPage() {
  const { id } = useParams<{ id: string }>()
  const sessionId = id ?? 'ses-014'
  const { data: auth } = useAuth()
  const { data, isLoading } = useInvites(id)
  const createMutation = useCreateInvite()
  const revokeMutation = useRevokeInvite()

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [revokeTarget, setRevokeTarget] = useState<ViewerInviteRecord | null>(null)
  const [label, setLabel] = useState('Khách VIP tháng 11')
  const [usageCap, setUsageCap] = useState(30)
  const [expiryHours, setExpiryHours] = useState(24)
  const [notice, setNotice] = useState<string | null>(null)

  const isOwner = Boolean(auth?.capabilities.canManageInvites)

  if (auth && !isOwner) {
    return (
      <EmptyState
        tone="warning"
        icon={<Lock className="h-6 w-6" />}
        title="Chỉ Chủ sở hữu mới có quyền quản lý Lời mời xem livestream"
        description="Vận hành viên không thể tạo, sao chép hoặc thu hồi liên kết mời khách xem live."
      />
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-72 w-full" />
      </div>
    )
  }

  const invites = data?.items ?? []
  const activeInvite =
    invites.find((i) => i.id === selectedId) ?? invites[0] ?? null

  const baseOrigin =
    typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1:5173'

  const handleCreate = async () => {
    const expiresAt = new Date(Date.now() + expiryHours * 3600 * 1000).toISOString()
    const created = await createMutation.mutateAsync({
      sessionId,
      label,
      usageCap,
      expiresAt,
    })
    setSelectedId(created.id)
    setCreateOpen(false)
    setNotice(
      `Đã tạo liên kết mời bất biến “${created.label}” (${created.usageCap} lượt). Đường dẫn và mã QR đã sẵn sàng chia sẻ.`,
    )
  }

  const handleRevoke = async () => {
    if (!revokeTarget) return
    const res = await revokeMutation.mutateAsync(revokeTarget.id)
    setRevokeTarget(null)
    setNotice(
      `Đã thu hồi liên kết “${res.invite.label}”. Đã chặn lượt vào mới và ngắt quyền ${res.ejectedCount} khách đang xem từ liên kết này.`,
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            Lời mời xem livestream & Mã QR
          </h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Tạo nhiều liên kết mời đặt tên bất biến kèm thời hạn và giới hạn lượt vào. Thu hồi liên kết sẽ ngắt khách đang xem từ liên kết đó.
          </p>
        </div>

        <Button
          variant="primary"
          leftIcon={<Plus className="h-4 w-4" />}
          onClick={() => setCreateOpen(true)}
        >
          Tạo lời mời mới
        </Button>
      </div>

      {notice ? <Banner severity="info" title="Cập nhật lời mời" description={notice} /> : null}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="lg:col-span-7 space-y-3">
          {invites.map((inv) => {
            const selected = activeInvite?.id === inv.id
            const badge =
              inv.status === 'ACTIVE'
                ? { label: 'Đang hoạt động', tone: 'success' as const }
                : inv.status === 'EXPIRED'
                  ? { label: 'Hết hạn', tone: 'warning' as const }
                  : inv.status === 'EXHAUSTED'
                    ? { label: 'Hết lượt', tone: 'neutral' as const }
                    : { label: 'Đã thu hồi', tone: 'danger' as const }

            return (
              <Card
                key={inv.id}
                padding="md"
                onClick={() => setSelectedId(inv.id)}
                className={cn(
                  'cursor-pointer transition-colors space-y-2.5',
                  selected
                    ? 'border-[var(--brand-amber)] bg-[var(--bg-hero)]'
                    : 'hover:border-[var(--border-strong)]',
                )}
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-bold text-[var(--text-primary)]">
                      {inv.label}
                    </p>
                    <p className="text-xs text-[var(--text-muted)] tabular-nums">
                      {inv.sessionCode} · Đã vào {inv.successfulAdmissions}/{inv.usageCap} lượt · Hết hạn {formatShortTime(inv.expiresAt)}
                    </p>
                  </div>
                  <StatusBadge label={badge.label} tone={badge.tone} />
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-[var(--border-default)] text-xs">
                  <span className="text-[var(--text-secondary)]">
                    Đang xem: <strong className="tabular-nums">{inv.activeGuestCount}</strong> · Chính sách bất biến (IM-D3)
                  </span>
                  {inv.status === 'ACTIVE' ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-[var(--status-danger-fg)]"
                      onClick={(e) => {
                        e.stopPropagation()
                        setRevokeTarget(inv)
                      }}
                    >
                      Thu hồi link
                    </Button>
                  ) : null}
                </div>
              </Card>
            )
          })}
        </div>

        <Card padding="md" className="lg:col-span-5 h-fit">
          {activeInvite ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-base font-bold">
                  Lời mời · {activeInvite.label}
                </h2>
                <StatusBadge
                  label={activeInvite.status === 'ACTIVE' ? 'Đang hoạt động' : 'Không còn hiệu lực'}
                  tone={activeInvite.status === 'ACTIVE' ? 'success' : 'danger'}
                />
              </div>

              <QrCodePreview
                url={`${baseOrigin}/live/${activeInvite.sessionId}?invite=${activeInvite.token}`}
                relativePath={`/live/${activeInvite.sessionId}?invite=${activeInvite.token}`}
                label={activeInvite.label}
                sessionCode={activeInvite.sessionCode}
                disabled={activeInvite.status !== 'ACTIVE'}
              />
            </div>
          ) : (
            <p className="text-sm text-[var(--text-muted)]">Chọn một liên kết mời để xem mã QR.</p>
          )}
        </Card>
      </div>

      {/* Create Invite Drawer */}
      <Drawer
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Tạo liên kết mời xem livestream"
        subtitle="Sau khi phát hành, thời hạn và số lượt không thể chỉnh sửa (IM-D3)."
      >
        <div className="space-y-4">
          <div>
            <label htmlFor="inv-label" className="block text-xs font-semibold mb-1.5">
              Tên nhóm / nhãn liên kết *
            </label>
            <input
              id="inv-label"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold mb-1.5">Thời hạn sử dụng</label>
            <div className="grid grid-cols-3 gap-2">
              {[2, 24, 72].map((h) => (
                <button
                  key={h}
                  type="button"
                  onClick={() => setExpiryHours(h)}
                  className={cn(
                    'h-9 rounded-[8px] border text-xs font-semibold cursor-pointer',
                    expiryHours === h
                      ? 'border-[var(--brand-amber)] bg-[var(--bg-hero)] text-[var(--text-primary)]'
                      : 'border-[var(--border-default)] text-[var(--text-secondary)]',
                  )}
                >
                  {h} giờ
                </button>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="inv-cap" className="block text-xs font-semibold mb-1.5">
              Số lượt vào thành công tối đa *
            </label>
            <input
              id="inv-cap"
              type="number"
              min={1}
              max={500}
              value={usageCap}
              onChange={(e) => setUsageCap(Number(e.target.value))}
              className="h-10 w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm tabular-nums"
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-[var(--border-default)]">
            <Button variant="secondary" onClick={() => setCreateOpen(false)}>
              Hủy
            </Button>
            <Button
              variant="primary"
              loading={createMutation.isPending}
              onClick={handleCreate}
            >
              Xác nhận tạo link & QR
            </Button>
          </div>
        </div>
      </Drawer>

      {/* Revoke Confirm Modal (IM-D4) */}
      <Modal
        open={Boolean(revokeTarget)}
        onClose={() => setRevokeTarget(null)}
        title="Thu hồi liên kết mời này?"
        description="Hành động này không thể hoàn tác và sẽ được ghi vào Nhật ký phiên."
        footer={
          <>
            <Button variant="secondary" onClick={() => setRevokeTarget(null)}>
              Hủy
            </Button>
            <Button
              variant="destructive"
              loading={revokeMutation.isPending}
              leftIcon={<ShieldAlert className="h-4 w-4" />}
              onClick={handleRevoke}
            >
              Xác nhận thu hồi
            </Button>
          </>
        }
      >
        <p className="text-sm text-[var(--text-secondary)]">
          Khách mới sẽ không thể dùng liên kết hoặc mã QR <strong>{revokeTarget?.label}</strong>. Toàn bộ khách đang xem đã vào từ liên kết này sẽ bị ngắt quyền ngay lập tức (không ảnh hưởng khách từ liên kết khác).
        </p>
      </Modal>
    </div>
  )
}
