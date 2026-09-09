import { ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError } from '@/api/client'
import * as api from '@/api/adminUsers'

export const useAdminUsersStore = defineStore('adminUsers', () => {
  const users = ref<api.AdminUser[]>([])
  const loading = ref(false)
  const error = ref<ApiError | null>(null)

  async function loadUsers(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      users.value = await api.listAdminUsers()
    } catch (caught) {
      error.value = caught instanceof ApiError ? caught : new ApiError(0)
    } finally {
      loading.value = false
    }
  }

  function replaceUser(updated: api.AdminUser): api.AdminUser {
    users.value = users.value.map((user) => (user.id === updated.id ? updated : user))
    return updated
  }

  async function createUser(payload: api.CreateAdminUserPayload): Promise<api.AdminUser> {
    const user = await api.createAdminUser(payload)
    users.value = [...users.value, user]
    return user
  }

  async function updateUser(
    userId: number,
    payload: api.UpdateAdminUserPayload,
  ): Promise<api.AdminUser> {
    return replaceUser(await api.updateAdminUser(userId, payload))
  }

  async function resetPassword(userId: number, password: string): Promise<api.AdminUser> {
    return replaceUser(await api.resetAdminUserPassword(userId, password))
  }

  return { users, loading, error, loadUsers, createUser, updateUser, resetPassword }
})
