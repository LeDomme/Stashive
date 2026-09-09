import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'

import HealthView from './HealthView.vue'

afterEach(() => {
  vi.unstubAllGlobals()
})

it('shows an available API connection after a successful health check', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'ok' }),
    }),
  )

  const wrapper = mount(HealthView)
  await flushPromises()

  expect(wrapper.get('[data-state]').attributes('data-state')).toBe('available')
  expect(wrapper.text()).toContain('API connection: available')
})
