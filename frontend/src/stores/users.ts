import { ref } from 'vue'
import { defineStore } from 'pinia'

import {
  changeUserStatus,
  createUser,
  deleteUser,
  fetchUsers,
  updateUser,
  type UserCreatePayload,
  type UserItem,
  type UserUpdatePayload,
} from '@/api/users'

export const useUserStore = defineStore('users', () => {
  const users = ref<UserItem[]>([])
  const loading = ref(false)

  /** 拉取用户列表，页面进入时调用 */
  async function load() {
    loading.value = true
    try {
      users.value = await fetchUsers()
    } finally {
      loading.value = false
    }
  }

  /** 把后端返回的最新数据写回列表里对应的那一行 */
  function merge(updated: UserItem) {
    const index = users.value.findIndex((item) => item.id === updated.id)
    if (index !== -1) {
      users.value[index] = updated
    }
  }

  async function create(payload: UserCreatePayload) {
    const created = await createUser(payload)
    users.value.push(created)
  }

  async function update(id: number, payload: UserUpdatePayload) {
    merge(await updateUser(id, payload))
  }

  async function changeStatus(id: number, status: 0 | 1) {
    merge(await changeUserStatus(id, status))
  }

  async function remove(id: number) {
    await deleteUser(id)
    users.value = users.value.filter((item) => item.id !== id)
  }

  return { users, loading, load, create, update, changeStatus, remove }
})
