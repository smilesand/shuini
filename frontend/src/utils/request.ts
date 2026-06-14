import axios from 'axios'
import type { AxiosError, InternalAxiosRequestConfig } from 'axios'

import {
  CLIENT_REQUEST_ID_HEADER,
  CLIENT_SESSION_ID_HEADER,
  buildClientRequestId,
  getClientSessionId,
  logRuntimeEvent,
} from './runtimeLogger'

interface RequestTraceMetadata {
  startedAt: number
  requestId: string
}

type TraceableRequestConfig = InternalAxiosRequestConfig & {
  metadata?: RequestTraceMetadata
}

function resolveRequestUrl(config?: { baseURL?: string; url?: string }): string {
  return `${config?.baseURL || ''}${config?.url || ''}` || '-'
}

function durationMs(config?: TraceableRequestConfig): number | null {
  const startedAt = config?.metadata?.startedAt
  if (!startedAt) {
    return null
  }
  return Number((performance.now() - startedAt).toFixed(2))
}

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 15000,
})

// ── 请求拦截器：自动附加 Authorization token ──────────────────
request.interceptors.request.use(config => {
  const traceConfig = config as TraceableRequestConfig
  const requestId = buildClientRequestId('api')
  traceConfig.metadata = {
    startedAt: performance.now(),
    requestId,
  }

  traceConfig.headers[CLIENT_SESSION_ID_HEADER] = getClientSessionId()
  traceConfig.headers[CLIENT_REQUEST_ID_HEADER] = requestId

  const token = localStorage.getItem('sc_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── 响应拦截器：统一处理 {code, message, data} 格式 ───────────
request.interceptors.response.use(
  res => {
    const traceConfig = res.config as TraceableRequestConfig
    const body = res.data

    logRuntimeEvent('INFO', 'API request completed', {
      event: 'api-response',
      requestId: traceConfig.metadata?.requestId,
      context: {
        method: traceConfig.method?.toUpperCase(),
        url: resolveRequestUrl(traceConfig),
        status: res.status,
        duration_ms: durationMs(traceConfig),
        backend_request_id: res.headers['x-request-id'] || null,
      },
    })

    if (body && typeof body.code === 'number') {
      if (body.code !== 0) {
        return Promise.reject(new Error(body.message || '请求失败'))
      }
      return body.data // 自动解包 data 字段
    }
    return body
  },
  err => {
    const axiosError = err as AxiosError
    const traceConfig = axiosError.config as TraceableRequestConfig | undefined
    const data = err.response?.data
    const msg = data?.message || data?.detail || err.message || '请求失败'

    logRuntimeEvent('ERROR', 'API request failed', {
      event: 'api-error',
      requestId: traceConfig?.metadata?.requestId,
      context: {
        method: traceConfig?.method?.toUpperCase(),
        url: resolveRequestUrl(traceConfig),
        status: axiosError.response?.status || null,
        duration_ms: durationMs(traceConfig),
        backend_request_id: axiosError.response?.headers?.['x-request-id'] || null,
        message: msg,
      },
    })

    return Promise.reject(new Error(msg))
  }
)

export default request
