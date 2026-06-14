import type { App, ComponentPublicInstance } from 'vue'
import type { Router } from 'vue-router'

export type RuntimeLogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'

interface RuntimeLogOptions {
  event?: string
  route?: string
  requestId?: string
  context?: Record<string, unknown>
}

interface RuntimeLogPayload {
  level: RuntimeLogLevel
  source: string
  event?: string
  message: string
  route?: string
  url?: string
  session_id: string
  request_id?: string
  user_agent: string
  created_at: string
  context: Record<string, unknown>
}

const CLIENT_LOG_ENDPOINT = '/api/client-logs'
const CLIENT_SESSION_STORAGE_KEY = 'sc_trace_session_id'

export const CLIENT_SESSION_ID_HEADER = 'X-Client-Session-ID'
export const CLIENT_REQUEST_ID_HEADER = 'X-Client-Request-ID'

let runtimeLoggingInstalled = false

function safeStorageGet(key: string): string | null {
  try {
    return window.sessionStorage.getItem(key)
  } catch {
    return null
  }
}

function safeLocalStorageGet(key: string): string | null {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function safeStorageSet(key: string, value: string): void {
  try {
    window.sessionStorage.setItem(key, value)
  } catch {
    // Ignore storage write failures in locked-down browser environments.
  }
}

function buildTraceId(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

function currentRoute(): string {
  return `${window.location.pathname}${window.location.search}${window.location.hash}`
}

function serializeValue(value: unknown, depth = 0, seen = new WeakSet<object>()): unknown {
  if (depth > 3) {
    return '[MaxDepth]'
  }

  if (value instanceof Error) {
    return {
      name: value.name,
      message: value.message,
      stack: value.stack,
    }
  }

  if (value == null || typeof value === 'number' || typeof value === 'boolean') {
    return value
  }

  if (typeof value === 'string') {
    return value.length <= 2000 ? value : `${value.slice(0, 2000)}...(truncated)`
  }

  if (Array.isArray(value)) {
    return value.slice(0, 20).map(item => serializeValue(item, depth + 1, seen))
  }

  if (typeof value === 'object') {
    const objectValue = value as Record<string, unknown>
    if (seen.has(objectValue)) {
      return '[Circular]'
    }
    seen.add(objectValue)
    return Object.fromEntries(
      Object.entries(objectValue).slice(0, 30).map(([key, item]) => {
        const normalizedKey = key.toLowerCase()
        if (normalizedKey.includes('password') || normalizedKey.includes('token') || normalizedKey.includes('authorization')) {
          return [key, '***']
        }
        return [key, serializeValue(item, depth + 1, seen)]
      }),
    )
  }

  return String(value)
}

function normalizeContext(context?: Record<string, unknown>): Record<string, unknown> {
  const user = safeLocalStorageGet('sc_user') || ''
  const isAdmin = safeLocalStorageGet('sc_admin') === '1'

  return {
    ...Object.fromEntries(
      Object.entries(context || {}).map(([key, value]) => [key, serializeValue(value)]),
    ),
    user: user || undefined,
    is_admin: user ? isAdmin : undefined,
  }
}

function sessionId(): string {
  const existing = safeStorageGet(CLIENT_SESSION_STORAGE_KEY)
  if (existing) {
    return existing
  }

  const generated = buildTraceId('session')
  safeStorageSet(CLIENT_SESSION_STORAGE_KEY, generated)
  return generated
}

function sendPayload(payload: RuntimeLogPayload): void {
  const body = JSON.stringify(payload)

  if (navigator.sendBeacon && body.length < 60_000) {
    const blob = new Blob([body], { type: 'application/json' })
    if (navigator.sendBeacon(CLIENT_LOG_ENDPOINT, blob)) {
      return
    }
  }

  void fetch(CLIENT_LOG_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
    keepalive: true,
    credentials: 'same-origin',
  }).catch(() => {
    // Avoid recursive logging when the logger transport itself is unavailable.
  })
}

function componentName(instance: ComponentPublicInstance | null): string {
  const typedInstance = instance as ComponentPublicInstance & {
    type?: { name?: string; __name?: string }
  }

  return typedInstance?.type?.name || typedInstance?.type?.__name || 'AnonymousComponent'
}

export function buildClientRequestId(prefix = 'req'): string {
  return buildTraceId(prefix)
}

export function getClientSessionId(): string {
  return sessionId()
}

export function logRuntimeEvent(
  level: RuntimeLogLevel,
  message: string,
  options: RuntimeLogOptions = {},
): void {
  sendPayload({
    level,
    source: 'frontend',
    event: options.event,
    message,
    route: options.route || currentRoute(),
    url: window.location.href,
    session_id: sessionId(),
    request_id: options.requestId,
    user_agent: navigator.userAgent,
    created_at: new Date().toISOString(),
    context: normalizeContext(options.context),
  })
}

export function installRuntimeLogging(app: App, router: Router): void {
  if (runtimeLoggingInstalled) {
    return
  }

  runtimeLoggingInstalled = true

  app.config.errorHandler = (error, instance, info) => {
    logRuntimeEvent('ERROR', 'Vue component error', {
      event: 'vue-error',
      route: router.currentRoute.value.fullPath,
      context: {
        component: componentName(instance),
        info,
        error,
      },
    })
  }

  window.addEventListener('error', event => {
    logRuntimeEvent('ERROR', 'Window error', {
      event: 'window-error',
      context: {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error,
      },
    })
  })

  window.addEventListener('unhandledrejection', event => {
    logRuntimeEvent('ERROR', 'Unhandled promise rejection', {
      event: 'unhandled-rejection',
      context: {
        reason: event.reason,
      },
    })
  })

  router.afterEach((to, from, failure) => {
    if (failure) {
      logRuntimeEvent('WARNING', 'Route navigation finished with failure', {
        event: 'route-navigation-failure',
        route: to.fullPath,
        context: {
          from: from.fullPath,
          failure: serializeValue(failure),
        },
      })
      return
    }

    logRuntimeEvent('INFO', 'Route navigation completed', {
      event: 'route-navigation',
      route: to.fullPath,
      context: {
        from: from.fullPath,
        to: to.fullPath,
        name: typeof to.name === 'string' ? to.name : String(to.name || ''),
      },
    })
  })

  logRuntimeEvent('INFO', 'Frontend runtime initialized', {
    event: 'frontend-startup',
    context: {
      href: window.location.href,
      referrer: document.referrer || '-',
      viewport: `${window.innerWidth}x${window.innerHeight}`,
    },
  })
}