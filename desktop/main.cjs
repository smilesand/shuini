const { app, BrowserWindow, dialog, ipcMain } = require('electron')
const { execSync, spawn } = require('node:child_process')
const fs = require('node:fs')
const http = require('node:http')
const https = require('node:https')
const net = require('node:net')
const path = require('node:path')

const PREFERRED_BACKEND_PORT = Number(process.env.SC_DESKTOP_PORT || 38000)
const originalConsole = {
  log: console.log.bind(console),
  info: console.info.bind(console),
  warn: console.warn.bind(console),
  error: console.error.bind(console),
}

let backendProcess = null
let backendPort = PREFERRED_BACKEND_PORT
let backendLogPath = null
let desktopLogPath = null
let logDirectoryPath = null
let isQuitting = false
let consoleCaptureInstalled = false

function startUrl() {
  return `http://127.0.0.1:${backendPort}`
}

function installRootDir() {
  return app.isPackaged ? path.dirname(process.execPath) : path.resolve(__dirname)
}

function ensureLogDirectory() {
  if (logDirectoryPath) {
    return logDirectoryPath
  }

  const candidate = path.join(installRootDir(), 'logs')
  fs.mkdirSync(candidate, { recursive: true })
  logDirectoryPath = candidate
  return logDirectoryPath
}

function formatLogValue(value) {
  if (value instanceof Error) {
    return value.stack || value.message
  }

  if (typeof value === 'string') {
    return value
  }

  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

function appendLogLine(filePath, line) {
  try {
    fs.appendFileSync(filePath, `${line}\n`, 'utf8')
  } catch (error) {
    originalConsole.error('Failed to append log line', error)
  }
}

function formatLogLine(level, message, details) {
  const suffix = details === undefined ? '' : ` ${formatLogValue(details)}`
  return `${new Date().toISOString()} ${level} ${message}${suffix}`
}

function writeDesktopLog(level, message, details) {
  if (!desktopLogPath) {
    desktopLogPath = path.join(ensureLogDirectory(), 'desktop.log')
  }

  appendLogLine(desktopLogPath, formatLogLine(level, message, details))
}

function writeBackendLog(text) {
  if (!backendLogPath) {
    backendLogPath = path.join(ensureLogDirectory(), 'backend-process.log')
  }

  appendLogLine(backendLogPath, formatLogLine('INFO', text))
}

function markLogSession(filePath, label) {
  appendLogLine(filePath, `\n===== ${label} ${new Date().toISOString()} pid=${process.pid} =====`)
}

function installConsoleCapture() {
  if (consoleCaptureInstalled) {
    return
  }

  consoleCaptureInstalled = true
  const levelMap = {
    log: 'INFO',
    info: 'INFO',
    warn: 'WARN',
    error: 'ERROR',
  }

  for (const methodName of Object.keys(levelMap)) {
    const originalMethod = originalConsole[methodName]
    console[methodName] = (...args) => {
      originalMethod(...args)
      writeDesktopLog(levelMap[methodName], `console.${methodName}`, args.map(formatLogValue).join(' '))
    }
  }
}

function logDirectory() {
  return ensureLogDirectory()
}

function describeStartupError(error) {
  const logDir = logDirectory()
  const message = error instanceof Error ? error.message : String(error)
  const stack = error instanceof Error && error.stack ? `\n\n${error.stack}` : ''
  return `${message}${stack}\n\nLogs: ${logDir}`
}

function initializeDesktopLogging() {
  const logDir = logDirectory()
  desktopLogPath = path.join(logDir, 'desktop.log')
  markLogSession(desktopLogPath, 'Desktop session')
  writeDesktopLog('INFO', 'Desktop logging initialized', {
    logDir,
    installDir: installRootDir(),
    packaged: app.isPackaged,
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node,
  })
  installConsoleCapture()
}

function resolveResourcePath(...segments) {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, ...segments)
  }

  return path.join(__dirname, ...segments)
}

function backendExecutablePath() {
  if (process.env.SC_BACKEND_BINARY) {
    return process.env.SC_BACKEND_BINARY
  }

  const executable = process.platform === 'win32' ? 'wtcmd-platform-backend.exe' : 'wtcmd-platform-backend'
  return resolveResourcePath('backend', executable)
}

function frontendDistPath() {
  if (process.env.SC_FRONTEND_DIST) {
    return process.env.SC_FRONTEND_DIST
  }

  return resolveResourcePath('frontend-dist')
}

function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function findAvailablePort(port) {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.unref()

    server.on('error', error => {
      if (port !== 0 && error && error.code === 'EADDRINUSE') {
        findAvailablePort(0).then(resolve).catch(reject)
        return
      }
      reject(error)
    })

    server.listen({ host: '127.0.0.1', port }, () => {
      const address = server.address()
      const resolvedPort = typeof address === 'object' && address ? address.port : port
      server.close(closeError => {
        if (closeError) {
          reject(closeError)
          return
        }
        resolve(resolvedPort)
      })
    })
  })
}

function probeServer() {
  return new Promise(resolve => {
    const request = http.get(startUrl(), response => {
      response.resume()
      resolve(response.statusCode && response.statusCode < 500)
    })

    request.on('error', () => resolve(false))
    request.setTimeout(2000, () => {
      request.destroy()
      resolve(false)
    })
  })
}

async function waitForServer(timeoutMs = 30000) {
  const startedAt = Date.now()
  while (Date.now() - startedAt < timeoutMs) {
    if (await probeServer()) {
      return
    }
    await wait(400)
  }

  throw new Error(`Timed out waiting for backend at ${startUrl()}`)
}

function pipeBackendLogs(stream, prefix) {
  if (!stream) {
    return
  }

  stream.on('data', chunk => {
    const text = String(chunk).trim()
    if (text) {
      console.log(`${prefix} ${text}`)
      writeBackendLog(`${prefix} ${text}`)
    }
  })
}

async function startBackend() {
  const executable = backendExecutablePath()
  const frontendDist = frontendDistPath()
  const logDir = logDirectory()

  if (!fs.existsSync(executable)) {
    throw new Error(`Backend executable not found: ${executable}`)
  }

  if (!fs.existsSync(frontendDist)) {
    throw new Error(`Frontend dist not found: ${frontendDist}`)
  }

  const userDataDir = app.getPath('userData')
  fs.mkdirSync(userDataDir, { recursive: true })
  backendLogPath = path.join(logDir, 'backend-process.log')
  markLogSession(backendLogPath, 'Backend subprocess')
  backendPort = await findAvailablePort(PREFERRED_BACKEND_PORT)

  if (backendPort !== PREFERRED_BACKEND_PORT) {
    writeDesktopLog('WARN', 'Preferred backend port unavailable, falling back', {
      preferredPort: PREFERRED_BACKEND_PORT,
      selectedPort: backendPort,
    })
  }

  writeDesktopLog('INFO', 'Launching backend process', {
    executable,
    frontendDist,
    userDataDir,
    logDir,
    backendPort,
  })
  writeBackendLog(`Launching backend on port ${backendPort}`)

  backendProcess = spawn(executable, [], {
    cwd: installRootDir(),
    env: {
      ...process.env,
      SC_HOST: '127.0.0.1',
      SC_PORT: String(backendPort),
      SC_FRONTEND_DIST: frontendDist,
      SC_LOG_DIR: logDir,
      SC_DB_PATH: path.join(userDataDir, 'data.db'),
      SC_EDITION: 'desktop',
      SC_CORS_ORIGINS: `${startUrl()},http://localhost:${backendPort}`,
    },
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
  })

  writeDesktopLog('INFO', 'Backend process spawned', { pid: backendProcess.pid })

  pipeBackendLogs(backendProcess.stdout, '[backend]')
  pipeBackendLogs(backendProcess.stderr, '[backend]')

  backendProcess.once('exit', code => {
    writeDesktopLog('ERROR', 'Backend process exited', {
      code: code ?? 'unknown',
      logDir,
      backendProcessLog: backendLogPath,
    })
    backendProcess = null
    if (!isQuitting) {
      const details = [
        `The local API process exited unexpectedly with code ${code ?? 'unknown'}.`,
        `Logs: ${logDir}`,
        `Desktop: ${desktopLogPath}`,
        `Backend Process: ${backendLogPath}`,
        `Backend App: ${path.join(logDir, 'app.log')}`,
        `Backend Error: ${path.join(logDir, 'error.log')}`,
      ].join('\n')
      dialog.showErrorBox('Backend stopped', details)
      app.quit()
    }
  })

  await waitForServer()
  writeDesktopLog('INFO', 'Backend server is reachable', { url: startUrl() })
}

function stopBackend() {
  if (!backendProcess || backendProcess.killed) {
    return
  }

  const pid = backendProcess.pid
  writeDesktopLog('INFO', 'Stopping backend process', { pid })

  if (process.platform === 'win32') {
    try {
      execSync(`taskkill /pid ${pid} /t /f`, {
        windowsHide: true,
        stdio: 'ignore',
        timeout: 5000,
      })
    } catch {
      // Process may have already exited; that's fine.
    }
  } else {
    try {
      backendProcess.kill('SIGTERM')
    } catch {
      // Process may have already exited.
    }
  }

  backendProcess = null
}

async function createWindow() {
  await startBackend()

  // ── 桌面版：检查授权状态。试用期内允许进入主窗口，到期后进入激活窗口。 ──
  let needActivation = false
  try {
    const backendUrl = startUrl()
    const statusResp = await fetch(`${backendUrl}/api/license/status`)
    const statusData = await statusResp.json()
    if (statusData.code === 0 && statusData.data && !statusData.data.can_use) {
      needActivation = true
      writeDesktopLog('INFO', 'License is not usable, showing activation window', statusData.data)
    } else if (statusData.code === 0 && statusData.data && !statusData.data.activated) {
      writeDesktopLog('INFO', 'Product is running in trial mode', statusData.data)
    }
  } catch (e) {
    writeDesktopLog('WARN', 'License status check failed, opening main window and letting renderer show API errors', e)
  }

  if (needActivation) {
    // 打开激活窗口 — 按优先级尝试多个路径
    let actHtmlPath = null
    const candidates = [
      // 打包后: resources/activation.html
      path.join(process.resourcesPath, 'activation.html'),
      // 另一个可能的打包路径
      path.join(resolveResourcePath('frontend-dist'), '..', 'activation.html'),
      // 开发模式: 与 main.cjs 同目录
      path.join(__dirname, 'activation.html'),
      // 开发模式: 项目根目录
      path.join(__dirname, '..', 'activation.html'),
    ]
    for (const p of candidates) {
      if (fs.existsSync(p)) {
        actHtmlPath = p
        break
      }
    }
    if (!actHtmlPath) {
      dialog.showErrorBox('文件缺失', `未找到激活页面文件。\n尝试过的路径:\n${candidates.join('\n')}`)
      app.quit()
      return
    }

    const actHtml = fs.readFileSync(actHtmlPath, 'utf-8')

    const actWin = new BrowserWindow({
      width: 460,
      height: 560,
      resizable: false,
      autoHideMenuBar: true,
      title: '产品激活',
      backgroundColor: '#1e3c72',
      webPreferences: {
        contextIsolation: true,
        sandbox: false,
        preload: path.join(__dirname, 'preload-activation.js'),
      },
    })

    actWin.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(actHtml)}`)

    // ── 激活窗口 IPC 处理 ──
    ipcMain.handle('license:status', async () => {
      const statusUrl = `${startUrl()}/api/license/status`
      return fetchJson(statusUrl)
    })

    ipcMain.handle('license:activate', async (_event, licenseCode) => {
      const activateUrl = `${startUrl()}/api/license/activate`
      return fetchJson(activateUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ license_code: licenseCode }),
      })
    })

    ipcMain.once('license:window-closed', () => {
      // 激活窗口关闭后，重新检查状态
      checkActivationAndProceed()
    })

    actWin.on('closed', () => {
      // fallback: 如果 preload 没发 closeWindow，X 按钮关闭时也要触发
      ipcMain.removeHandler('license:status')
      ipcMain.removeHandler('license:activate')
      checkActivationAndProceed()
    })

    return
  }

  createMainWindow()
}

/** 通过 Node.js http 模块请求后端 API（避免 data: URL 跨域问题） */
function fetchJson(url, options = {}) {
  return new Promise((resolve, reject) => {
    const parsedUrl = new URL(url)
    const module = parsedUrl.protocol === 'https:' ? https : http

    const reqOptions = {
      hostname: parsedUrl.hostname,
      port: parsedUrl.port,
      path: parsedUrl.pathname + parsedUrl.search,
      method: options.method || 'GET',
      headers: options.headers || {},
      timeout: 10000,
    }

    if (options.body) {
      reqOptions.headers['Content-Length'] = Buffer.byteLength(options.body)
    }

    const req = module.request(reqOptions, res => {
      let data = ''
      res.on('data', chunk => { data += chunk })
      res.on('end', () => {
        try {
          resolve(JSON.parse(data))
        } catch {
          reject(new Error(`Invalid JSON: ${data.slice(0, 200)}`))
        }
      })
    })

    req.on('error', err => reject(err))
    req.on('timeout', () => { req.destroy(); reject(new Error('Request timeout')) })

    if (options.body) {
      req.write(options.body)
    }
    req.end()
  })
}

/** 检查授权状态，激活成功或仍可使用则进入主窗口，否则退出 */
async function checkActivationAndProceed() {
  let canUse = false
  try {
    const statusData = await fetchJson(`${startUrl()}/api/license/status`)
    if (statusData.code === 0 && statusData.data && statusData.data.can_use) {
      canUse = true
    }
  } catch (e) {
    writeDesktopLog('WARN', 'Activation re-check failed', e)
  }

  if (canUse) {
    createMainWindow()
  } else {
    writeDesktopLog('INFO', 'License is still unavailable after activation window closed — quitting')
    app.quit()
  }
}

async function createMainWindow() {
  const window = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 1200,
    minHeight: 760,
    show: false,
    autoHideMenuBar: true,
    backgroundColor: '#f4f7fb',
    webPreferences: {
      contextIsolation: true,
      sandbox: true,
    },
  })

  window.on('unresponsive', () => {
    writeDesktopLog('ERROR', 'Browser window became unresponsive')
  })

  window.on('closed', () => {
    writeDesktopLog('INFO', 'Browser window closed')
  })

  window.webContents.on('did-finish-load', () => {
    writeDesktopLog('INFO', 'Renderer finished loading', { url: window.webContents.getURL() })
  })

  window.webContents.on('did-fail-load', (_event, errorCode, errorDescription, validatedURL, isMainFrame) => {
    writeDesktopLog('ERROR', 'Renderer failed to load', {
      errorCode,
      errorDescription,
      validatedURL,
      isMainFrame,
    })
  })

  window.webContents.on('console-message', (_event, level, message, line, sourceId) => {
    writeDesktopLog(level >= 2 ? 'WARN' : 'INFO', 'Renderer console message', {
      level,
      message,
      line,
      sourceId,
    })
  })

  window.webContents.on('render-process-gone', (_event, details) => {
    writeDesktopLog('ERROR', 'Renderer process gone', details)
  })

  window.once('ready-to-show', () => {
    writeDesktopLog('INFO', 'Browser window ready to show')
    window.show()
  })

  await window.loadURL(startUrl())
  writeDesktopLog('INFO', 'Window loadURL completed', { url: startUrl() })
}

initializeDesktopLogging()

process.on('uncaughtException', error => {
  writeDesktopLog('CRITICAL', 'Unhandled exception in desktop process', error)
  if (app.isReady()) {
    dialog.showErrorBox('Desktop crashed', describeStartupError(error))
  }
})

process.on('unhandledRejection', reason => {
  writeDesktopLog('ERROR', 'Unhandled promise rejection in desktop process', reason)
})

app.on('render-process-gone', (_event, _webContents, details) => {
  writeDesktopLog('ERROR', 'App-level render process gone', details)
})

app.on('child-process-gone', (_event, details) => {
  writeDesktopLog('ERROR', 'Electron child process gone', details)
})

app.on('before-quit', () => {
  isQuitting = true
  writeDesktopLog('INFO', 'App before-quit received')
})

app.on('will-quit', () => {
  writeDesktopLog('INFO', 'App will-quit received — performing synchronous cleanup')
  stopBackend()
})

app.on('window-all-closed', () => {
  writeDesktopLog('INFO', 'All windows closed', { platform: process.platform })
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('activate', () => {
  writeDesktopLog('INFO', 'App activate received', { openWindows: BrowserWindow.getAllWindows().length })
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow().catch(error => {
      writeDesktopLog('ERROR', 'Create window failed during activate', error)
      dialog.showErrorBox('Startup failed', describeStartupError(error))
      app.quit()
    })
  }
})

// ── 单实例锁 ──
// 关键：桌面版的数据库以「整库内存快照 + 提交时整体加密落盘」方式工作。若允许多开，
// 每个实例都会启动一个后端、各自持有独立的内存副本，并在提交（如授权状态轮询写 last_seen）
// 时用自己的旧快照覆盖磁盘，互相清掉对方刚写入的数据——表现为「新建记录后看不到、像是
// 只存在内存里」。因此这里强制单实例：再次启动只聚焦已有窗口。
const gotSingleInstanceLock = app.requestSingleInstanceLock()
if (!gotSingleInstanceLock) {
  writeDesktopLog('WARN', 'Another instance is already running — quitting this one')
  app.quit()
} else {
  app.on('second-instance', () => {
    writeDesktopLog('INFO', 'Second instance launch detected — focusing existing window')
    const windows = BrowserWindow.getAllWindows()
    if (windows.length > 0) {
      const win = windows[0]
      if (win.isMinimized()) {
        win.restore()
      }
      win.focus()
    }
  })

  app.whenReady().then(() => {
    writeDesktopLog('INFO', 'Electron app is ready')
    createWindow().catch(error => {
      writeDesktopLog('ERROR', 'Create window failed during startup', error)
      dialog.showErrorBox('Startup failed', describeStartupError(error))
      app.quit()
    })
  })
}
