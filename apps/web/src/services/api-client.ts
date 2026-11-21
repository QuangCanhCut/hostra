import type { UserRole } from '@/types/auth'
import type { MockScenarioKey } from '@/types/scenario'

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly requestId?: string

  constructor(message: string, status: number, code: string, requestId?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
  }
}

export interface RequestContext {
  scenario: MockScenarioKey
  role: UserRole
}

export async function apiRequest<T>(
  path: string,
  context: RequestContext,
  init?: RequestInit,
): Promise<T> {
  const headers = new Headers(init?.headers)
  headers.set('Accept', 'application/json')
  headers.set('X-Hostra-Scenario', context.scenario)
  headers.set('X-Hostra-Role', context.role)
  if (init?.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(path, { ...init, headers })
  const contentType = response.headers.get('content-type') ?? ''
  const payload = contentType.includes('application/json')
    ? await response.json()
    : null

  if (!response.ok) {
    const message =
      (payload && typeof payload.message === 'string' && payload.message) ||
      'Không thể tải dữ liệu từ hệ thống. Vui lòng thử lại.'
    const code =
      (payload && typeof payload.code === 'string' && payload.code) ||
      `HTTP_${response.status}`
    const requestId =
      payload && typeof payload.requestId === 'string' ? payload.requestId : undefined
    throw new ApiError(message, response.status, code, requestId)
  }

  return payload as T
}
