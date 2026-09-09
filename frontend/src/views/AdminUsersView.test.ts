import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/client'
import * as adminApi from '@/api/adminUsers'
import { useAuthStore } from '@/stores/auth'
import AdminUsersView from './AdminUsersView.vue'

vi.mock('@/api/adminUsers', () => ({
  listAdminUsers: vi.fn(),
  createAdminUser: vi.fn(),
  updateAdminUser: vi.fn(),
  resetAdminUserPassword: vi.fn(),
}))

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/admin/users', name: 'admin-users', component: AdminUsersView },
    { path: '/collections', name: 'collections', component: AdminUsersView },
    { path: '/login', name: 'login', component: AdminUsersView },
  ],
})

const admin = { id: 1, username: 'admin', display_name: 'Admin User', is_instance_admin: true }
const member = {
  id: 2,
  username: 'member',
  display_name: 'Member User',
  is_instance_admin: false,
  is_active: true,
  created_at: '2026-09-09T00:00:00Z',
}

async function mountView(currentUser = admin) {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = currentUser
  await router.push('/admin/users')
  const wrapper = mount(AdminUsersView, { global: { plugins: [pinia, router] } })
  await flushPromises()
  return { wrapper, auth }
}

beforeEach(() => {
  vi.mocked(adminApi.listAdminUsers).mockResolvedValue([
    { ...member },
    { ...admin, is_active: true, created_at: '2026-09-09T00:00:00Z' },
  ])
})

afterEach(() => vi.clearAllMocks())

describe('AdminUsersView', () => {
  it('renders safe user data for an instance administrator', async () => {
    const { wrapper } = await mountView()

    expect(wrapper.get('[aria-label="Local users"]').text()).toContain('Member User (member)')
    expect(wrapper.text()).toContain('Instance admin')
    expect(wrapper.text()).not.toContain('password_hash')
  })

  it('creates a user without retaining entered password fields', async () => {
    vi.mocked(adminApi.createAdminUser).mockResolvedValue({ ...member, id: 3, username: 'new-user' })
    const { wrapper } = await mountView()
    const createForm = wrapper.findAll('form').find((form) => form.text().includes('Create local user'))!

    await createForm.findAll('input')[0].setValue(' new-user ')
    await createForm.findAll('input')[1].setValue(' New User ')
    await createForm.findAll('input')[2].setValue('a sufficiently long password')
    await createForm.trigger('submit.prevent')
    await flushPromises()

    expect(adminApi.createAdminUser).toHaveBeenCalledWith({
      username: 'new-user',
      display_name: 'New User',
      password: 'a sufficiently long password',
      is_instance_admin: false,
    })
    expect(createForm.findAll('input')[2].element.value).toBe('')
  })

  it('shows a safe duplicate-username error', async () => {
    vi.mocked(adminApi.createAdminUser).mockRejectedValue(new ApiError(409))
    const { wrapper } = await mountView()
    const createForm = wrapper.findAll('form').find((form) => form.text().includes('Create local user'))!

    await createForm.findAll('input')[0].setValue('member')
    await createForm.findAll('input')[2].setValue('a sufficiently long password')
    await createForm.trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain('Username is already in use.')
  })

  it('edits a display name and promotes then demotes another user', async () => {
    vi.mocked(adminApi.updateAdminUser)
      .mockResolvedValueOnce({ ...member, display_name: 'Edited Member' })
      .mockResolvedValueOnce({ ...member, is_instance_admin: true })
      .mockResolvedValueOnce({ ...member, is_instance_admin: false })
    const { wrapper } = await mountView()
    const row = wrapper.get('.admin-user-row')

    await row.findAll('button').find((button) => button.text() === 'Edit')!.trigger('click')
    await row.get('.inline-form input').setValue('Edited Member')
    await row.get('.inline-form').trigger('submit.prevent')
    await flushPromises()
    expect(adminApi.updateAdminUser).toHaveBeenCalledWith(2, { display_name: 'Edited Member' })

    await row.findAll('button').find((button) => button.text() === 'Make admin')!.trigger('click')
    await flushPromises()
    expect(row.text()).toContain('Instance admin')
    await row.findAll('button').find((button) => button.text() === 'Remove admin')!.trigger('click')
    await flushPromises()
    expect(adminApi.updateAdminUser).toHaveBeenLastCalledWith(2, { is_instance_admin: false })
  })

  it('confirms disabling and supports enabling a user', async () => {
    vi.mocked(adminApi.updateAdminUser)
      .mockResolvedValueOnce({ ...member, is_active: false })
      .mockResolvedValueOnce({ ...member, is_active: true })
    const { wrapper } = await mountView()
    const row = wrapper.get('.admin-user-row')

    await row.findAll('button').find((button) => button.text() === 'Disable')!.trigger('click')
    expect(wrapper.text()).toContain('Their current sessions will end')
    await wrapper.findAll('button').find((button) => button.text() === 'Confirm disable')!.trigger('click')
    await flushPromises()
    expect(adminApi.updateAdminUser).toHaveBeenCalledWith(2, { is_active: false })
    await row.findAll('button').find((button) => button.text() === 'Enable')!.trigger('click')
    await flushPromises()
    expect(adminApi.updateAdminUser).toHaveBeenLastCalledWith(2, { is_active: true })
  })

  it('shows the backend last-admin protection response', async () => {
    vi.mocked(adminApi.updateAdminUser).mockRejectedValue(new ApiError(409))
    const { wrapper } = await mountView()
    const adminRow = wrapper.findAll('.admin-user-row')[1]

    await adminRow.findAll('button').find((button) => button.text() === 'Remove admin')!.trigger('click')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain('At least one active instance admin must remain.')
  })

  it('resets another user password and clears the password inputs', async () => {
    vi.mocked(adminApi.resetAdminUserPassword).mockResolvedValue({ ...member })
    const { wrapper } = await mountView()
    const row = wrapper.get('.admin-user-row')

    await row.findAll('button').find((button) => button.text() === 'Reset password')!.trigger('click')
    const resetForm = wrapper.findAll('form')[1]
    await resetForm.findAll('input')[0].setValue('a sufficiently long new password')
    await resetForm.findAll('input')[1].setValue('a sufficiently long new password')
    await resetForm.trigger('submit.prevent')
    await flushPromises()

    expect(adminApi.resetAdminUserPassword).toHaveBeenCalledWith(2, 'a sufficiently long new password')
    expect(wrapper.text()).toContain('Password reset for Member User')
    expect(wrapper.findAll('input[type="password"]').every((input) => input.element.value === '')).toBe(true)
  })

  it.each([
    ['reset', { reset: true }, 'login'],
    ['disable', { is_active: false }, 'login'],
    ['demotion', { is_instance_admin: false }, 'collections'],
  ])('handles self %s by updating local auth and navigation', async (action, response, routeName) => {
    const self = { ...admin, is_active: true, created_at: '2026-09-09T00:00:00Z' }
    vi.mocked(adminApi.listAdminUsers).mockResolvedValue([self])
    if (action === 'reset') vi.mocked(adminApi.resetAdminUserPassword).mockResolvedValue({ ...self })
    else vi.mocked(adminApi.updateAdminUser).mockResolvedValue({ ...self, ...response })
    const { wrapper, auth } = await mountView()
    const row = wrapper.get('.admin-user-row')

    if (action === 'reset') {
      await row.findAll('button').find((button) => button.text() === 'Reset password')!.trigger('click')
      const resetForm = wrapper.findAll('form')[1]
      await resetForm.findAll('input')[0].setValue('a sufficiently long new password')
      await resetForm.findAll('input')[1].setValue('a sufficiently long new password')
      await resetForm.trigger('submit.prevent')
    } else if (action === 'disable') {
      await row.findAll('button').find((button) => button.text() === 'Disable')!.trigger('click')
      await wrapper.findAll('button').find((button) => button.text() === 'Confirm disable')!.trigger('click')
    } else {
      await row.findAll('button').find((button) => button.text() === 'Remove admin')!.trigger('click')
    }
    await flushPromises()

    if (routeName === 'login') expect(auth.user).toBeNull()
    expect(router.currentRoute.value.name).toBe(routeName)
  })
})
