import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  Check,
  CheckCircle2,
  Send,
  Sparkles,
  X,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Banner } from '@/components/ui/Banner'
import { Skeleton } from '@/components/ui/Skeleton'
import { useAuth } from '@/features/auth/hooks/useAuth'
import {
  useApproveStory,
  useRequestStoryAi,
  useResolveStoryAi,
  useStoryPlan,
  useUpdateStoryArcs,
} from '@/features/story-planner/hooks/useStoryPlan'
import { cn } from '@/lib/cn'

export function StoryPlannerPage() {
  const { id } = useParams<{ id: string }>()
  const sessionId = id ?? 'ses-015'
  const { data: auth } = useAuth()
  const { data: plan, isLoading } = useStoryPlan(sessionId)
  const updateArcsMutation = useUpdateStoryArcs(sessionId)
  const aiSuggestMutation = useRequestStoryAi(sessionId)
  const aiResolveMutation = useResolveStoryAi(sessionId)
  const approveMutation = useApproveStory(sessionId)

  const [selectedArcId, setSelectedArcId] = useState<string | null>(null)
  const [prompt, setPrompt] = useState(
    'Giới thiệu nguồn gốc sản phẩm trước, sau đó mới nói về cách bảo quản.',
  )
  const [notice, setNotice] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const isOwner = Boolean(auth?.capabilities.canApproveContent)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (!plan) {
    return (
      <Card padding="lg" className="space-y-3">
        <p className="text-sm font-semibold">Không tìm thấy kế hoạch kịch bản cho phiên này.</p>
        <Link to="/studio/sessions">
          <Button variant="secondary">Quay lại danh sách phiên</Button>
        </Link>
      </Card>
    )
  }

  const activeArc =
    plan.arcs.find((a) => a.id === selectedArcId) ?? plan.arcs[0] ?? null
  const reviewedCount = plan.arcs.filter((a) => a.reviewed).length
  const allReviewed = reviewedCount === plan.arcs.length && plan.arcs.length > 0

  const handleToggleReviewed = async (arcId: string) => {
    setErrorMsg(null)
    const nextArcs = plan.arcs.map((a) =>
      a.id === arcId ? { ...a, reviewed: !a.reviewed } : a,
    )
    try {
      await updateArcsMutation.mutateAsync({
        arcs: nextArcs,
        summary: 'Cập nhật trạng thái rà soát đoạn kịch bản',
      })
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Không thể cập nhật.')
    }
  }

  const handleMoveArc = async (index: number, delta: -1 | 1) => {
    const target = index + delta
    if (target < 0 || target >= plan.arcs.length) return
    setErrorMsg(null)
    const next = [...plan.arcs]
    const [moved] = next.splice(index, 1)
    next.splice(target, 0, moved)
    try {
      await updateArcsMutation.mutateAsync({
        arcs: next,
        summary: `Đổi thứ tự đoạn “${moved.title}”`,
      })
      setNotice('Đã cập nhật thứ tự kịch bản nháp. Phiên bản mới cần Chủ sở hữu duyệt lại.')
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Không thể đổi thứ tự.')
    }
  }

  const handleAskAi = async () => {
    if (!prompt.trim()) return
    setErrorMsg(null)
    setNotice(null)
    try {
      await aiSuggestMutation.mutateAsync(prompt)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Không thể tạo đề xuất AI.')
    }
  }

  const handleResolveProposal = async (action: 'APPLY' | 'REJECT') => {
    setErrorMsg(null)
    try {
      await aiResolveMutation.mutateAsync(action)
      setNotice(
        action === 'APPLY'
          ? 'Đã áp dụng đề xuất AI vào bản nháp (chưa tự động phê duyệt). Hãy rà soát từng đoạn và duyệt phiên bản mới.'
          : 'Đã bỏ qua đề xuất chỉnh sửa từ Trợ lý AI.',
      )
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Không thể xử lý đề xuất.')
    }
  }

  const handleApproveRevision = async () => {
    setErrorMsg(null)
    setNotice(null)
    try {
      await approveMutation.mutateAsync()
      setNotice(
        `Đã phê duyệt toàn bộ phiên bản kịch bản v${plan.planRevision}. Trạng thái Readiness của phiên đã được cập nhật.`,
      )
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Không thể phê duyệt kịch bản.')
    }
  }

  const approvalBadge =
    plan.approvalStatus === 'APPROVED'
      ? { label: `Đã duyệt v${plan.approvedRevision}`, tone: 'success' as const }
      : plan.approvalStatus === 'INVALIDATED'
        ? { label: 'Cần duyệt lại (SKU thay đổi)', tone: 'danger' as const }
        : { label: `Chờ duyệt v${plan.planRevision}`, tone: 'warning' as const }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Link
            to={`/studio/sessions/${sessionId}`}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] mb-1"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Quay lại {plan.sessionCode}
          </Link>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="font-display text-[26px] sm:text-[32px] font-bold leading-[1.16] tracking-[-0.02em] text-[var(--text-primary)]">
              Lập kế hoạch nội dung · {plan.sessionCode}
            </h1>
            <StatusBadge label={approvalBadge.label} tone={approvalBadge.tone} />
          </div>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            {plan.sessionTitle} · Sắp xếp Story Arcs, chỉnh bằng Trợ lý AI (diff) và duyệt toàn bộ phiên bản.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Link to={`/studio/sessions/${sessionId}/readiness`}>
            <Button variant="secondary" size="sm">
              Mở Readiness Checklist
            </Button>
          </Link>
          {isOwner ? (
            <Button
              variant="primary"
              size="sm"
              disabled={!allReviewed}
              loading={approveMutation.isPending}
              leftIcon={<CheckCircle2 className="h-4 w-4" />}
              onClick={handleApproveRevision}
            >
              Duyệt toàn bộ v{plan.planRevision} ({reviewedCount}/{plan.arcs.length})
            </Button>
          ) : null}
        </div>
      </div>

      {plan.dirtyReason ? (
        <Banner severity="warning" title="Kịch bản cần Chủ sở hữu rà soát lại" description={plan.dirtyReason} />
      ) : null}
      {notice ? <Banner severity="info" title="Cập nhật kịch bản" description={notice} /> : null}
      {errorMsg ? <Banner severity="danger" title="Không thể thực hiện" description={errorMsg} /> : null}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        {/* Left: Timeline Story Arcs (60%) */}
        <div className="xl:col-span-7 space-y-4">
          <Card padding="md" className="space-y-3">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-base font-bold">Timeline kịch bản ({plan.arcs.length} đoạn)</h2>
              <span className="text-xs text-[var(--text-muted)] tabular-nums">
                Đã rà soát: {reviewedCount}/{plan.arcs.length}
              </span>
            </div>

            <ol className="space-y-2.5">
              {plan.arcs.map((arc, idx) => {
                const isSelected = activeArc?.id === arc.id
                return (
                  <li
                    key={arc.id}
                    className={cn(
                      'rounded-[10px] border border-l-[3px] p-3.5 transition-colors',
                      isSelected
                        ? 'border-[var(--border-strong)] border-l-[var(--accent-gold)] bg-[var(--bg-raised)]'
                        : 'border-[var(--border-default)] border-l-[var(--border-strong)] bg-[var(--bg-surface)]',
                    )}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <button
                        type="button"
                        onClick={() => setSelectedArcId(arc.id)}
                        className="min-w-0 flex-1 text-left cursor-pointer"
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="inline-flex h-6 w-6 items-center justify-center rounded-full [background:var(--cta-primary-bg)] text-xs font-bold text-[var(--cta-primary-fg)] tabular-nums">
                            0{arc.position}
                          </span>
                          <span className="text-sm font-bold text-[var(--text-primary)]">
                            {arc.title}
                          </span>
                          <span className="text-xs text-[var(--text-muted)] tabular-nums">
                            ~{arc.durationMin} phút
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-[var(--text-secondary)]">
                          {arc.skuLabel} · {arc.topic}
                        </p>
                      </button>

                      <div className="flex shrink-0 items-center gap-1">
                        {isOwner ? (
                          <>
                            <button
                              type="button"
                              aria-label={`Đưa đoạn ${arc.position} lên`}
                              disabled={idx === 0 || updateArcsMutation.isPending}
                              onClick={() => handleMoveArc(idx, -1)}
                              className="flex h-8 w-8 items-center justify-center rounded-[6px] border border-[var(--border-default)] text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] disabled:opacity-40 cursor-pointer"
                            >
                              <ArrowUp className="h-3.5 w-3.5" />
                            </button>
                            <button
                              type="button"
                              aria-label={`Đưa đoạn ${arc.position} xuống`}
                              disabled={idx === plan.arcs.length - 1 || updateArcsMutation.isPending}
                              onClick={() => handleMoveArc(idx, 1)}
                              className="flex h-8 w-8 items-center justify-center rounded-[6px] border border-[var(--border-default)] text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] disabled:opacity-40 cursor-pointer"
                            >
                              <ArrowDown className="h-3.5 w-3.5" />
                            </button>
                          </>
                        ) : null}
                      </div>
                    </div>

                    <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[var(--border-default)]">
                      <span className="text-[11px] text-[var(--text-muted)]">
                        Nguồn: {arc.factRefs.join(' · ') || 'Tri thức đã duyệt'}
                      </span>
                      <button
                        type="button"
                        disabled={!isOwner || updateArcsMutation.isPending}
                        onClick={() => handleToggleReviewed(arc.id)}
                        className={cn(
                          'inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold cursor-pointer disabled:opacity-60',
                          arc.reviewed
                            ? 'bg-[var(--status-success-bg)] text-[var(--status-success-fg)]'
                            : 'bg-[var(--bg-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]',
                        )}
                      >
                        <Check className="h-3 w-3" />
                        {arc.reviewed ? 'Đã rà soát' : 'Đánh dấu đã rà soát'}
                      </button>
                    </div>
                  </li>
                )
              })}
            </ol>
          </Card>

          {activeArc ? (
            <Card padding="md" className="space-y-2.5">
              <p className="text-xs font-semibold text-[var(--text-muted)]">
                Xem trước lời thoại minh họa · Đoạn 0{activeArc.position}
              </p>
              <p className="text-sm text-[var(--text-primary)] leading-relaxed">
                “{activeArc.previewText}”
              </p>
              <p className="text-xs text-[var(--text-secondary)]">
                Trích dẫn bằng chứng: <span className="font-medium">{activeArc.factRefs.join(' · ')}</span>
              </p>
            </Card>
          ) : null}
        </div>

        {/* Right: AI Editing Assistant (40%) */}
        <div className="xl:col-span-5 space-y-4">
          <Card padding="md" className="space-y-4">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-[var(--brand-amber)]" />
              <h2 className="text-base font-bold">Trợ lý AI chỉnh sửa kịch bản</h2>
            </div>
            <p className="text-xs text-[var(--text-secondary)]">
              Nhập yêu cầu bằng tiếng Việt. Trợ lý AI chỉ đề xuất bản vá kèm so sánh Trước/Sau và không tự động phê duyệt.
            </p>

            <div className="space-y-2">
              <label htmlFor="ai-story-prompt" className="sr-only">
                Yêu cầu chỉnh sửa kịch bản
              </label>
              <textarea
                id="ai-story-prompt"
                rows={3}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Ví dụ: Rút ngắn phần mở đầu, ưu tiên giới thiệu nguồn gốc trước giá bán..."
                className="w-full rounded-[8px] border border-[var(--border-strong)] bg-[var(--bg-surface)] p-3 text-sm text-[var(--text-primary)]"
              />
              <Button
                variant="primary"
                className="w-full"
                loading={aiSuggestMutation.isPending}
                leftIcon={<Send className="h-4 w-4" />}
                onClick={handleAskAi}
              >
                Gửi yêu cầu đến Trợ lý AI (Mô phỏng)
              </Button>
            </div>

            {plan.lastProposal && plan.lastProposal.status === 'PROPOSAL_READY' ? (
              <div className="rounded-[12px] border border-[var(--border-strong)] bg-[var(--bg-subtle)] p-4 space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-bold text-[var(--text-primary)]">
                    Đề xuất thay đổi (Trước / Sau)
                  </span>
                  <StatusBadge label="Chờ bạn chấp nhận" tone="info" />
                </div>

                <p className="text-xs text-[var(--text-secondary)]">{plan.lastProposal.summary}</p>

                {plan.lastProposal.unsupportedWarning ? (
                  <Banner
                    severity="danger"
                    title="Đã loại bỏ nội dung thiếu chứng cứ"
                    description={plan.lastProposal.unsupportedWarning}
                  />
                ) : null}

                <div className="space-y-2 text-xs">
                  <div className="rounded-[8px] bg-[var(--bg-surface)] p-2.5 border border-[var(--border-default)]">
                    <p className="font-semibold text-[var(--text-muted)]">Trước:</p>
                    <p className="mt-0.5 text-[var(--text-secondary)]">{plan.lastProposal.beforeSummary}</p>
                  </div>
                  <div className="rounded-[8px] bg-[var(--bg-surface)] p-2.5 border border-[var(--brand-amber)]">
                    <p className="font-semibold text-[var(--text-primary)]">Sau (Đề xuất):</p>
                    <p className="mt-0.5 text-[var(--text-primary)]">{plan.lastProposal.afterSummary}</p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="primary"
                    size="sm"
                    disabled={!isOwner}
                    loading={aiResolveMutation.isPending}
                    leftIcon={<Check className="h-3.5 w-3.5" />}
                    onClick={() => handleResolveProposal('APPLY')}
                  >
                    Áp dụng vào bản nháp
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    loading={aiResolveMutation.isPending}
                    leftIcon={<X className="h-3.5 w-3.5" />}
                    onClick={() => handleResolveProposal('REJECT')}
                  >
                    Bỏ qua đề xuất
                  </Button>
                </div>
              </div>
            ) : null}
          </Card>

          <Card padding="md" className="space-y-2.5">
            <h3 className="text-sm font-bold">Lịch sử phiên bản kịch bản</h3>
            <ul className="divide-y divide-[var(--border-default)] text-xs">
              {plan.revisionHistory.map((h) => (
                <li key={`${h.revision}-${h.timestamp}`} className="py-2">
                  <p className="font-semibold text-[var(--text-primary)]">
                    v{h.revision} · {h.summary}
                  </p>
                  <p className="text-[var(--text-muted)]">{h.actor}</p>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </div>
  )
}
