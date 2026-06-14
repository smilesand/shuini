import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { logout as apiLogout } from '../api/auth'

const TOKEN_KEY  = 'sc_token'
const USER_KEY   = 'sc_user'
const ADMIN_KEY  = 'sc_admin'

export const useAuthStore = defineStore('auth', () => {
  const token    = ref<string>(localStorage.getItem(TOKEN_KEY) ?? '') // 登录令牌
  const username = ref<string>(localStorage.getItem(USER_KEY)  ?? '') // 当前用户名
  const isAdmin  = ref<boolean>(localStorage.getItem(ADMIN_KEY) === '1') // 是否管理员

  const isLoggedIn = computed(() => !!token.value) // 是否已登录

  function setAuth(t: string, u: string, admin: boolean = false) {
    token.value    = t
    username.value = u
    isAdmin.value  = admin
    localStorage.setItem(TOKEN_KEY, t)
    localStorage.setItem(USER_KEY,  u)
    localStorage.setItem(ADMIN_KEY, admin ? '1' : '0')
  }

  function clearAuth() {
    token.value    = ''
    username.value = ''
    isAdmin.value  = false
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    localStorage.removeItem(ADMIN_KEY)
  }

  async function logout(options: { revokeSession?: boolean } = {}) {
    const { revokeSession = true } = options
    const currentToken = token.value

    if (revokeSession && currentToken) {
      try {
        await apiLogout()
      } catch {
        // Best effort: local logout should still succeed if the session is already invalid.
      }
    }

    clearAuth()
  }

  return { token, username, isAdmin, isLoggedIn, setAuth, clearAuth, logout }
})
