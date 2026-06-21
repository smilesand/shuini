import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getLicenseStatus, type LicenseStatus } from '../api/license'

export const useLicenseStore = defineStore('license', () => {
  const status = ref<LicenseStatus | null>(null)
  const loaded = ref(false)

  /** 当已获取到状态且不可用时锁定整个应用。获取失败时不锁定，避免误伤。 */
  const locked = computed(() => (status.value ? !status.value.can_use : false))

  /** 是否为需要激活的桌面/单机版（Web 版无需激活）。 */
  const isDesktop = computed(() => status.value?.edition === 'desktop')

  /**
   * 桌面端未激活时的提示文案（试用剩余天数 / 未激活）；其余情况返回 null。
   * 用于在界面常驻展示，免去用户手动点开「激活软件」查看。
   */
  const trialNotice = computed<string | null>(() => {
    const s = status.value
    if (!s || s.edition !== 'desktop' || s.activated) {
      return null
    }
    if (s.trial && s.can_use) {
      return `试用版 · 剩余 ${s.trial_days_left ?? 0} 天`
    }
    return '未激活'
  })

  async function fetchStatus(): Promise<LicenseStatus | null> {
    try {
      status.value = await getLicenseStatus()
    } catch {
      // 获取失败（例如 Web 部署未提供该接口）时保持解锁。
      status.value = null
    } finally {
      loaded.value = true
    }
    return status.value
  }

  function clear() {
    status.value = null
    loaded.value = false
  }

  return { status, loaded, locked, isDesktop, trialNotice, fetchStatus, clear }
})
