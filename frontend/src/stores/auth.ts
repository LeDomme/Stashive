import { ref } from 'vue'
import { defineStore } from 'pinia'
import * as api from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<api.CurrentUser | null>(null)
  const setupRequired = ref(false)
  const ready = ref(false)
  async function bootstrap(): Promise<void> {
    const status = await api.fetchAuthStatus()
    setupRequired.value = status.setup_required
    user.value = status.authenticated ? await api.fetchCurrentUser() : null
    ready.value = true
  }
  async function signIn(username: string, password: string): Promise<void> { user.value = await api.login(username, password); setupRequired.value = false }
  async function completeSetup(token: string, username: string, displayName: string, password: string): Promise<void> { user.value = await api.setup(token, username, displayName, password); setupRequired.value = false }
  async function signOut(): Promise<void> { await api.logout(); user.value = null }
  async function refreshUser(): Promise<void> { user.value = await api.fetchCurrentUser() }
  function clearAuth(): void { user.value = null }
  return { user, setupRequired, ready, bootstrap, signIn, completeSetup, signOut, refreshUser, clearAuth }
})
