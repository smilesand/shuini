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

// 防止同一页面加载周期内多次触发 401 跳转
let _authExpiredRedirected = false

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

    // 401 未授权：令牌无效或已过期，清除本地认证状态并跳转到登录页
    if (axiosError.response?.status === 401) {
      localStorage.removeItem('sc_token')
      localStorage.removeItem('sc_user')
      localStorage.removeItem('sc_admin')
      // 避免重复跳转（例如多个并发请求同时返回 401）
      if (_authExpiredRedirected) {
        return Promise.reject(new Error('登录状态已过期，请重新登录'))
      }
      _authExpiredRedirected = true
      // 登录接口本身返回 401 时不跳转（用户名密码错误等）
      const url = resolveRequestUrl(traceConfig)
      if (!url.includes('/auth/login')) {
        window.location.href = '/login?expired=1'
        return Promise.reject(new Error('登录状态已过期，请重新登录'))
      }
    }

    return Promise.reject(new Error(msg))
  }
)

export default request
