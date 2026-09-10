<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError } from '@/api/client'
import type { AdminUser, CreateAdminUserPayload } from '@/api/adminUsers'
import { useAdminUsersStore } from '@/stores/adminUsers'
import { useAuthStore } from '@/stores/auth'

const adminUsers = useAdminUsersStore()
const auth = useAuthStore()
const router = useRouter()
const username = ref('')
const displayName = ref('')
const initialPassword = ref('')
const createAsAdmin = ref(false)
const createError = ref('')
const creating = ref(false)
const editingUserId = ref<number | null>(null)
const editDisplayName = ref('')
const actionError = ref('')
const pendingDisable = ref<AdminUser | null>(null)
const passwordUser = ref<AdminUser | null>(null)
const newPassword = ref('')
const confirmPassword = ref('')
const passwordSuccess = ref('')
const resettingPassword = ref(false)

const isInstanceAdmin = computed(() => auth.user?.is_instance_admin === true)

onMounted(() => adminUsers.loadUsers())

function userLabel(user: AdminUser): string {
  return user.display_name || user.username
}

function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return 'This action could not be completed. Please try again.'
  if (error.status === 401) return 'Your session has ended. Please sign in again.'
  if (error.status === 403) return 'You do not have permission to manage users.'
  if (error.status === 404) return 'That user is no longer available.'
  if (error.status === 409) return 'At least one active instance admin must remain.'
  if (error.status === 422) return 'Check the entered details and try again.'
  return 'This action could not be completed. Please try again.'
}

async function handleSelfChange(updated: AdminUser): Promise<void> {
  if (updated.id !== auth.user?.id) return
  if (!updated.is_active) {
    auth.clearAuth()
    await router.push({ name: 'login' })
  } else if (!updated.is_instance_admin) {
    auth.user = {
      id: updated.id,
      username: updated.username,
      display_name: updated.display_name,
      is_instance_admin: false,
    }
    await router.push({ name: 'collections' })
  }
}

async function createUser(): Promise<void> {
  creating.value = true
  createError.value = ''
  const payload: CreateAdminUserPayload = {
    username: username.value.trim(),
    display_name: displayName.value.trim() || null,
    password: initialPassword.value,
    is_instance_admin: createAsAdmin.value,
  }
  try {
    await adminUsers.createUser(payload)
    username.value = ''
    displayName.value = ''
    initialPassword.value = ''
    createAsAdmin.value = false
  } catch (error) {
    createError.value = error instanceof ApiError && error.status === 409
      ? 'Username is already in use.'
      : errorMessage(error)
  } finally {
    creating.value = false
  }
}

function beginEdit(user: AdminUser): void {
  editingUserId.value = user.id
  editDisplayName.value = user.display_name ?? ''
  actionError.value = ''
}

async function saveDisplayName(user: AdminUser): Promise<void> {
  actionError.value = ''
  try {
    await adminUsers.updateUser(user.id, { display_name: editDisplayName.value.trim() || null })
    editingUserId.value = null
  } catch (error) {
    actionError.value = errorMessage(error)
  }
}

async function updateUser(user: AdminUser, payload: { is_instance_admin?: boolean; is_active?: boolean }): Promise<void> {
  actionError.value = ''
  try {
    const updated = await adminUsers.updateUser(user.id, payload)
    await handleSelfChange(updated)
  } catch (error) {
    actionError.value = errorMessage(error)
  }
}

async function disableUser(): Promise<void> {
  if (!pendingDisable.value) return
  const user = pendingDisable.value
  pendingDisable.value = null
  await updateUser(user, { is_active: false })
}

function openPasswordReset(user: AdminUser): void {
  passwordUser.value = user
  newPassword.value = ''
  confirmPassword.value = ''
  passwordSuccess.value = ''
  actionError.value = ''
}

async function resetPassword(): Promise<void> {
  if (!passwordUser.value) return
  if (newPassword.value !== confirmPassword.value) {
    actionError.value = 'The two passwords do not match.'
    return
  }
  resettingPassword.value = true
  actionError.value = ''
  try {
    const updated = await adminUsers.resetPassword(passwordUser.value.id, newPassword.value)
    newPassword.value = ''
    confirmPassword.value = ''
    passwordUser.value = null
    if (updated.id === auth.user?.id) {
      auth.clearAuth()
      await router.push({ name: 'login' })
    } else {
      passwordSuccess.value = `Password reset for ${userLabel(updated)}. They need to sign in again.`
    }
  } catch (error) {
    actionError.value = errorMessage(error)
  } finally {
    resettingPassword.value = false
  }
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value))
}
</script>

<template>
  <section class="page-content" aria-labelledby="admin-users-heading">
    <div class="page-heading">
      <div><p class="eyebrow">Instance administration</p><h1 id="admin-users-heading">Local users</h1><p>Manage access to this Stashive installation. Collection permissions remain separate.</p></div>
    </div>
    <div v-if="!isInstanceAdmin" class="empty-state state-error" role="alert"><h2>Admin area unavailable</h2><p>You do not have permission to manage local users.</p></div>
    <template v-else>
      <form class="collection-form panel" @submit.prevent="createUser">
        <h2>Create local user</h2>
        <label>Username<input v-model="username" required autocomplete="off" /></label>
        <label>Display name <span class="optional">optional</span><input v-model="displayName" autocomplete="name" /></label>
        <label>Initial password<input v-model="initialPassword" type="password" minlength="12" required autocomplete="new-password" /></label>
        <label class="checkbox-label"><input v-model="createAsAdmin" type="checkbox" /> Make this user an instance admin</label>
        <p v-if="createError" class="form-error" role="alert">{{ createError }}</p>
        <button type="submit" :disabled="creating">{{ creating ? 'Creating…' : 'Create user' }}</button>
      </form>

      <div v-if="adminUsers.error" class="empty-state state-error" role="alert"><h2>Users unavailable</h2><p>{{ errorMessage(adminUsers.error) }}</p></div>
      <section v-else class="users-panel panel" aria-labelledby="user-list-heading">
        <h2 id="user-list-heading">Users</h2>
        <p v-if="passwordSuccess" class="success-message" role="status">{{ passwordSuccess }}</p>
        <p v-if="actionError" class="form-error" role="alert">{{ actionError }}</p>
        <ul class="admin-user-list" aria-label="Local users">
          <li v-for="user in adminUsers.users" :key="user.id" class="admin-user-row" :class="{ 'is-disabled': !user.is_active }">
            <div><strong>{{ userLabel(user) }}</strong> <span>({{ user.username }})</span><small>Created {{ formatDate(user.created_at) }}</small></div>
            <div class="user-badges"><span>{{ user.is_active ? 'Active' : 'Disabled' }}</span><span>{{ user.is_instance_admin ? 'Instance admin' : 'User' }}</span></div>
            <div class="user-actions">
              <button type="button" class="button-secondary button-compact" @click="beginEdit(user)">Edit</button>
              <button type="button" class="button-secondary button-compact" @click="openPasswordReset(user)">Reset password</button>
              <button type="button" class="button-secondary button-compact" @click="updateUser(user, { is_instance_admin: !user.is_instance_admin })">{{ user.is_instance_admin ? 'Remove admin' : 'Make admin' }}</button>
              <button v-if="user.is_active" type="button" class="button-danger button-compact" @click="pendingDisable = user">Disable</button>
              <button v-else type="button" class="button-secondary button-compact" @click="updateUser(user, { is_active: true })">Enable</button>
            </div>
            <form v-if="editingUserId === user.id" class="inline-form" @submit.prevent="saveDisplayName(user)"><label>Display name<input v-model="editDisplayName" autocomplete="name" /></label><div class="action-row"><button type="submit">Save</button><button type="button" class="button-secondary" @click="editingUserId = null">Cancel</button></div></form>
          </li>
        </ul>
      </section>

      <section v-if="pendingDisable" class="confirmation panel" aria-labelledby="disable-heading"><h2 id="disable-heading">Disable {{ userLabel(pendingDisable) }}?</h2><p>They will no longer be able to sign in. Their current sessions will end, while their collection ownership and memberships remain.</p><div class="action-row"><button type="button" class="button-danger" @click="disableUser">Confirm disable</button><button type="button" class="button-secondary" @click="pendingDisable = null">Cancel</button></div></section>

      <section v-if="passwordUser" class="confirmation panel" aria-labelledby="password-heading"><h2 id="password-heading">Reset password for {{ userLabel(passwordUser) }}</h2><p>Existing sessions will be ended and a new login will be required.</p><form class="collection-form" @submit.prevent="resetPassword"><label>New password<input v-model="newPassword" type="password" minlength="12" required autocomplete="new-password" /></label><label>Confirm new password<input v-model="confirmPassword" type="password" minlength="12" required autocomplete="new-password" /></label><div class="action-row"><button type="submit" :disabled="resettingPassword">{{ resettingPassword ? 'Resetting…' : 'Reset password' }}</button><button type="button" class="button-secondary" :disabled="resettingPassword" @click="passwordUser = null">Cancel</button></div></form></section>
    </template>
  </section>
</template>
