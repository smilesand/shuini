<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SidebarLayout from './components/SidebarLayout.vue'
import { useAuthStore } from './stores/authStore'
import { useLicenseStore } from './stores/licenseStore'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const licenseStore = useLicenseStore()
const isPublic = computed(() => route.meta['public'])

// 登录后（进入受保护页面时）拉取授权状态；若已锁定则强制跳转激活页。
watch(
  () => [authStore.isLoggedIn, isPublic.value] as const,
  async ([loggedIn, pub]) => {
    if (loggedIn && !pub && !licenseStore.loaded) {
      await licenseStore.fetchStatus()
      if (licenseStore.locked && route.name !== 'activation') {
        router.push('/activation')
      }
    }
    if (!loggedIn) {
      licenseStore.clear()
    }
  },
  { immediate: true },
)
</script>

<template>
  <RouterView v-if="isPublic" />
  <SidebarLayout v-else />
</template>
