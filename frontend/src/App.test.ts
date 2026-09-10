import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { describe, expect, it } from 'vitest'

import { useAuthStore } from '@/stores/auth'
import App from './App.vue'

function mountApp(isInstanceAdmin: boolean) {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = {
    id: 1,
    username: 'user',
    display_name: null,
    is_instance_admin: isInstanceAdmin,
  }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/collections', component: { template: '<div />' } },
      { path: '/admin/users', component: { template: '<div />' } },
    ],
  })
  return mount(App, { global: { plugins: [pinia, router] } })
}

describe('App navigation', () => {
  it('opens the burger menu and scopes administration to instance admins', async () => {
    const admin = mountApp(true)
    const trigger = admin.find('[aria-label="Open application menu"]')
    expect(trigger.attributes('aria-expanded')).toBe('false')
    await trigger.trigger('click')
    expect(trigger.attributes('aria-expanded')).toBe('true')
    expect(admin.text()).toContain('Collections')
    expect(admin.text()).toContain('Administration')
    expect(admin.text()).toContain('Sign out')

    const member = mountApp(false)
    expect(member.text()).not.toContain('Administration')
  })
})
