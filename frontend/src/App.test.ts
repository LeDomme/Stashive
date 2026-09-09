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
  it('shows the user-management navigation item only to instance admins', () => {
    expect(mountApp(true).text()).toContain('Users')
    expect(mountApp(false).text()).not.toContain('Users')
  })
})
