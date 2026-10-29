import http from '@/api/http'

export interface UserInfo {
  id: number
  username: string
  name: string
  role: 'admin' | 'student'
}

export interface LoginResult {
  access_token: string
  token_type: string
  expires_in: number
  user: UserInfo
}

export function login(username: string, password: string) {
  return http
    .post<LoginResult>('/auth/login', { username, password })
    .then((response) => response.data)
}

export function fetchCurrentUser() {
  return http.get<UserInfo>('/auth/me').then((response) => response.data)
}

export function logout() {
  return http.post<{ message: string }>('/auth/logout').then((response) => response.data)
}
