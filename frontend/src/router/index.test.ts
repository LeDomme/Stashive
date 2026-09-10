import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, expect, it } from 'vitest'

import router from '@/router'
import { useAuthStore } from '@/stores/auth'

beforeEach(() => {
  setActivePinia(createPinia())
})

it('redirects a normal user away from the direct admin-users route', async () => {
  const auth = useAuthStore()
  auth.ready = true
  auth.setupRequired = false
  auth.user = { id: 2, username: 'member', display_name: null, is_instance_admin: false }

  await router.push('/admin/users')

  expect(router.currentRoute.value.name).toBe('collections')
})

it('uses collections as the authenticated home route', async () => {
  const auth = useAuthStore()
  auth.ready = true
  auth.setupRequired = false
  auth.user = { id: 1, username: 'owner', display_name: null, is_instance_admin: true }

  await router.push('/')

  expect(router.currentRoute.value.name).toBe('collections')
})
