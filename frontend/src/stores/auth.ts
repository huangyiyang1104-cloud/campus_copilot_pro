import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { login as loginApi, logout as logoutApi, type UserInfo } from '@/api/auth'
import { clearSession, getCachedUser, getToken, setCachedUser, setToken } from '@/api/token'

export type { UserInfo }

export const useAuthStore = defineStore('auth', () => {
  const token = ref(getToken())
  const user = ref<UserInfo | null>(getCachedUser<UserInfo>())

  const isLoggedIn = computed(() => Boolean(token.value))
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(username: string, password: string) {
    const result = await loginApi(username, password)

    token.value = result.access_token
    user.value = result.user
    setToken(result.access_token)
    setCachedUser(result.user)
  }

  async function logout() {
    // 先让后端把 Redis 里的 RT 删掉、清 Cookie，失败也要清本地
    try {
      await logoutApi()
    } catch {
      // 令牌本来就失效时忽略，本地状态照样清
    } finally {
      token.value = ''
      user.value = null
      clearSession()
    }
  }

  return { token, user, isLoggedIn, isAdmin, login, logout }
})
