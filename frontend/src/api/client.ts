import type { ApiErrorPayload } from '@/types/api'

const API_ROOT = '/api/v1'
const DEFAULT_TIMEOUT_MS = 5_000

export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly requestId: string | null,
    readonly action: string | null,
  ) {
    super(message)
  }
}

function isApiErrorPayload(value: unknown): value is ApiErrorPayload {
  if (typeof value !== 'object' || value === null || !('error' in value)) return false
  const error = value.error
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    typeof error.code === 'string' &&
    'message' in error &&
    typeof error.message === 'string'
  )
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown | FormData
  timeoutMs?: number
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(
    () => controller.abort(),
    options.timeoutMs ?? DEFAULT_TIMEOUT_MS,
  )
  try {
    let requestBody: BodyInit | undefined
    if (options.body instanceof FormData) requestBody = options.body
    else if (options.body !== undefined) requestBody = JSON.stringify(options.body)
    const isFormData = requestBody instanceof FormData
    const response = await fetch(`${API_ROOT}${path}`, {
      method: options.method ?? 'GET',
      headers: {
        Accept: 'application/json',
        ...(options.body === undefined || isFormData ? {} : { 'Content-Type': 'application/json' }),
      },
      body: requestBody,
      signal: controller.signal,
    })
    if (response.status === 204) return undefined as T
    const payload: unknown = await response.json()
    if (!response.ok) {
      if (isApiErrorPayload(payload)) {
        throw new ApiError(
          payload.error.message,
          payload.error.code,
          payload.error.request_id,
          payload.error.action,
        )
      }
      throw new ApiError('服务返回了无法识别的错误。', 'PM-NETWORK-002', null, '请稍后重试。')
    }
    return payload as T
  } catch (error: unknown) {
    if (error instanceof ApiError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('连接后端超时。', 'PM-NETWORK-001', null, '确认后端正在运行后重试。')
    }
    throw new ApiError('无法连接本机后端。', 'PM-NETWORK-001', null, '请启动后端并重试。')
  } finally {
    window.clearTimeout(timeout)
  }
}

export function apiGet<T>(path: string, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  return apiRequest<T>(path, { timeoutMs })
}
