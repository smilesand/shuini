import { onBeforeUnmount, onMounted } from 'vue'
import { saveRecord, type SaveRecordPayload } from '../api/records'

/**
 * 定时自动保存组合式函数。
 *
 * 设计目标（见需求）：用户在填写数据时，每隔一段时间把数据保存到服务端。
 *
 * 策略约定：
 *  - 仅「更新」已经保存过的记录（payload 必须带 id）。不会自动新建草稿记录，
 *    因此不会在记录列表中产生多余条目。
 *  - 通过对 `record_data` 做 JSON 序列化得到指纹，只有内容发生变化才会发起保存，
 *    避免无意义的重复写入。
 *  - 切换到另一条记录时只重建基线、不触发保存。
 *  - 自动保存失败时静默处理，等待下一次定时重试，不打断用户填写。
 */
export interface UseAutoSaveOptions {
  /** 自动保存间隔（毫秒），默认 15000。 */
  intervalMs?: number
  /**
   * 解析当前可保存的 payload。
   * 返回 `null`（或 payload 不带 id）表示当前不满足自动保存条件，跳过本次。
   */
  resolve: () => SaveRecordPayload | null
  /** 保存成功后的回调，用于同步 store 中的记录/试配状态。 */
  onSaved?: (id: number, payload: SaveRecordPayload) => void
}

export function useAutoSave(options: UseAutoSaveOptions) {
  const intervalMs = options.intervalMs ?? 15000
  let timer: ReturnType<typeof setInterval> | null = null
  let saving = false
  let lastRecordId: number | null | undefined
  let lastSignature = ''

  function signatureOf(payload: SaveRecordPayload): string {
    try {
      return JSON.stringify(payload.record_data ?? {})
    } catch {
      return ''
    }
  }

  async function flush(): Promise<void> {
    if (saving) return

    const payload = options.resolve()
    // 仅更新已保存过的记录。
    if (!payload || payload.id == null) return

    const signature = signatureOf(payload)

    // 切换到另一条记录：只刷新基线，不保存。
    if (payload.id !== lastRecordId) {
      lastRecordId = payload.id
      lastSignature = signature
      return
    }

    if (signature === lastSignature) return

    saving = true
    try {
      const res = await saveRecord(payload)
      lastSignature = signature
      options.onSaved?.(res.id, payload)
    } catch {
      // 静默失败，等待下一次定时重试。
    } finally {
      saving = false
    }
  }

  function handleVisibility() {
    if (document.visibilityState === 'hidden') {
      void flush()
    }
  }

  onMounted(() => {
    // 进入页面时先建立基线，避免立即把未改动的载入数据重复写回。
    const payload = options.resolve()
    if (payload && payload.id != null) {
      lastRecordId = payload.id
      lastSignature = signatureOf(payload)
    }
    timer = setInterval(() => { void flush() }, intervalMs)
    document.addEventListener('visibilitychange', handleVisibility)
  })

  onBeforeUnmount(() => {
    if (timer) clearInterval(timer)
    timer = null
    document.removeEventListener('visibilitychange', handleVisibility)
    // 离开页面前再尝试保存一次最新数据。
    void flush()
  })

  return { flush }
}
