import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'

import { clearSession, getToken, setToken } from '@/api/token'

interface RetriableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

const http = axios.create({
  baseURL: '/api',
  timeout: 15_000,
})

/** 请求拦截：自动带上 AT */
http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 同一时刻只允许发一次刷新请求，其余请求等它的结果
let refreshing: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  // 用裸 axios，避免再进拦截器造成递归
  const { data } = await axios.post<{ access_token: string }>('/api/auth/refresh')
  setToken(data.access_token)
  return data.access_token
}

/** 响应拦截：AT 失效 → 用 RT 换新 AT → 重放原请求 */
http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetriableConfig | undefined
    const url = config?.url ?? ''
    const isAuthRequest = url.includes('/auth/login') || url.includes('/auth/refresh')

    if (error.response?.status === 401 && config && !config._retry && !isAuthRequest) {
      config._retry = true

      try {
        refreshing ??= refreshAccessToken().finally(() => {
          refreshing = null
        })

        const token = await refreshing
        config.headers.Authorization = `Bearer ${token}`
        return await http(config)
      } catch {
        // RT 也无效，清掉本地状态回登录页
        clearSession()
        window.location.assign('/login')
        return await Promise.reject(error)
      }
    }

    return await Promise.reject(error)
  },
)

/** 从后端错误里取提示文案（detail 可能是字符串或 { code, message }） */
export function getErrorMessage(error: unknown, fallback = '请求失败，请稍后重试'): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (detail && typeof detail === 'object' && 'message' in detail) {
      return String(detail.message)
    }
    return error.message || fallback
  }
  return fallback
}

export default http
