import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import { Check, Copy, Download, ExternalLink } from 'lucide-react'
import { Button, ButtonLink } from '@/components/ui/Button'

export interface QrCodePreviewProps {
  url: string
  relativePath: string
  label: string
  sessionCode: string
  disabled?: boolean
}

export function QrCodePreview({
  url,
  relativePath,
  label,
  sessionCode,
  disabled = false,
}: QrCodePreviewProps) {
  const [dataUrl, setDataUrl] = useState<string>('')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    let active = true
    QRCode.toDataURL(url, {
      width: 240,
      margin: 2,
      color: { dark: '#21160C', light: '#FFFFFF' },
    })
      .then((res) => {
        if (active) setDataUrl(res)
      })
      .catch(() => {
        if (active) setDataUrl('')
      })
    return () => {
      active = false
    }
  }, [url])

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(true)
    }
  }

  const handleDownloadPng = () => {
    if (!dataUrl || disabled) return
    const safeName = `${sessionCode}_${label}`
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-zA-Z0-9_-]+/g, '_')
    const a = document.createElement('a')
    a.href = dataUrl
    a.download = `HOSTRA_QR_${safeName}.png`
    document.body.appendChild(a)
    a.click()
    a.remove()
  }

  return (
    <div className="space-y-4 text-center">
      <div className="mx-auto inline-flex flex-col items-center rounded-[14px] border border-[var(--border-strong)] bg-white p-4 shadow-[var(--shadow-card)]">
        {dataUrl ? (
          <img
            src={dataUrl}
            alt={`Mã QR mời xem live cho ${label}`}
            className={`h-48 w-48 ${disabled ? 'opacity-30 grayscale' : ''}`}
          />
        ) : (
          <div className="flex h-48 w-48 items-center justify-center text-xs text-[#665748]">
            Đang tạo mã QR...
          </div>
        )}
        <p className="mt-2 text-xs font-semibold text-[#2A2018]">
          {sessionCode} · {label}
        </p>
      </div>

      <p className="break-all rounded-[8px] bg-[var(--bg-subtle)] px-3 py-2 text-xs text-[var(--text-secondary)]">
        {url}
      </p>

      <div className="flex flex-col gap-2">
        <Button
          variant="primary"
          disabled={disabled}
          leftIcon={copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          onClick={handleCopy}
        >
          {copied ? 'Đã sao chép đường dẫn' : 'Sao chép đường dẫn'}
        </Button>

        <Button
          variant="secondary"
          disabled={disabled || !dataUrl}
          leftIcon={<Download className="h-4 w-4" />}
          onClick={handleDownloadPng}
        >
          Tải mã QR (PNG)
        </Button>

        {!disabled ? (
          <ButtonLink
            to={relativePath}
            variant="ghost"
            size="sm"
            className="w-full"
            leftIcon={<ExternalLink className="h-3.5 w-3.5" />}
          >
            Mở thử phòng xem khách (Viewer Room)
          </ButtonLink>
        ) : null}
      </div>

      <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
        Mã QR mã hóa đúng URL lời mời, không chứa token media nội bộ. Khi chạy localhost, thiết bị khác chỉ quét vào được nếu dev server mở qua địa chỉ mạng cục bộ.
      </p>
    </div>
  )
}
