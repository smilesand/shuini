import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getLicenseStatus, type LicenseStatus } from '../api/license'

export const useLicenseStore = defineStore('license', () => {
  const status = ref<LicenseStatus | null>(null)
  const loaded = ref(false)

  /** 当已获取到状态且不可用时锁定整个应用。获取失败时不锁定，避免误伤。 */
  const locked = computed(() => (status.value ? !status.value.can_use : false))

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

  return { status, loaded, locked, fetchStatus, clear }
})
