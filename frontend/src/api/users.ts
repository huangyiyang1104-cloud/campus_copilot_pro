import http from '@/api/http'

/** 与后端 schemas/users.py 的 UserItem 对应（不含密码） */
export interface UserItem {
  id: number
  username: string
  name: string
  role: 'admin' | 'student'
  email: string | null
  phone: string | null
  avatar: string | null
  status: 0 | 1
  create_time: string
  update_time: string
}

/** 新增用户提交的字段，对应 UserCreate */
export interface UserCreatePayload {
  username: string
  password: string
  name: string
  role: 'admin' | 'student'
  email?: string
  phone?: string
  avatar?: string
  status: 0 | 1
}

/** 编辑用户提交的字段，对应 UserUpdate：不传的字段表示不改 */
export interface UserUpdatePayload {
  username?: string
  password?: string
  name?: string
  role?: 'admin' | 'student'
  email?: string
  phone?: string
  avatar?: string
  status?: 0 | 1
}

export function fetchUsers() {
  return http.get<UserItem[]>('/users').then((response) => response.data)
}

export function createUser(payload: UserCreatePayload) {
  return http.post<UserItem>('/users', payload).then((response) => response.data)
}

export function updateUser(id: number, payload: UserUpdatePayload) {
  return http.put<UserItem>(`/users/${id}`, payload).then((response) => response.data)
}

export function changeUserStatus(id: number, status: 0 | 1) {
  return http
    .patch<UserItem>(`/users/${id}/status`, { status })
    .then((response) => response.data)
}

export function deleteUser(id: number) {
  return http.delete<{ message: string }>(`/users/${id}`).then((response) => response.data)
}
