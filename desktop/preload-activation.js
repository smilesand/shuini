/**
 * 激活窗口预加载脚本
 * 通过 IPC 与主进程通信，主进程代理 HTTP 请求到后端。
 * 解决 data: URL 无法直接 fetch 到 http://127.0.0.1 的问题。
 */
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('activationAPI', {
  /** 获取激活状态（含机器指纹） */
  getStatus() {
    return ipcRenderer.invoke('license:status')
  },
  /** 执行激活 */
  activate(licenseCode) {
    return ipcRenderer.invoke('license:activate', licenseCode)
  },
  /** 关闭窗口（通知主进程重新检查状态） */
  closeWindow() {
    ipcRenderer.send('license:window-closed')
  },
})
