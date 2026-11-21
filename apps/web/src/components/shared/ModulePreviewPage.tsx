import { Link } from 'react-router-dom'
import { ArrowLeft, Layers } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { StatusBadge } from '@/components/ui/StatusBadge'

export interface ModulePreviewPageProps {
  title: string
  description: string
  milestoneLabel: string
  highlights: string[]
}

export function ModulePreviewPage({
  title,
  description,
  milestoneLabel,
  highlights,
}: ModulePreviewPageProps) {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">{title}</h1>
            <StatusBadge label={milestoneLabel} tone="info" />
          </div>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">{description}</p>
        </div>
        <Link to="/studio/dashboard">
          <Button variant="secondary" leftIcon={<ArrowLeft className="h-4 w-4" />}>
            Quay lại Tổng quan
          </Button>
        </Link>
      </div>

      <Card padding="lg" className="space-y-4">
        <div className="flex items-center gap-2.5 text-[var(--text-primary)]">
          <Layers className="h-5 w-5 text-[var(--text-secondary)]" aria-hidden="true" />
          <h2 className="text-base font-semibold">Phạm vi triển khai theo đặc tả HOSTRA</h2>
        </div>
        <ul className="grid gap-2.5 sm:grid-cols-2">
          {highlights.map((item) => (
            <li
              key={item}
              className="rounded-[10px] border border-[var(--border-default)] bg-[var(--bg-subtle)] px-3.5 py-2.5 text-sm text-[var(--text-secondary)]"
            >
              {item}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}
