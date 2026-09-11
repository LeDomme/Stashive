import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import * as collectionsApi from '@/api/collections'
import CollectionSettingsView from './CollectionSettingsView.vue'

vi.mock('@/api/collections')

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/collections/:collectionId/settings', name: 'collection-settings', component: CollectionSettingsView },
    { path: '/collections/:collectionId/catalog', name: 'catalog', component: CollectionSettingsView },
    { path: '/collections/:collectionId/inventory', name: 'inventory', component: CollectionSettingsView },
    { path: '/collections/:collectionId/locations', name: 'locations', component: CollectionSettingsView },
    { path: '/collections', name: 'collections', component: CollectionSettingsView },
  ],
})

async function view(role: 'owner' | 'admin' | 'editor' | 'viewer') {
  vi.mocked(collectionsApi.getCollection).mockResolvedValue({ id: 1, name: 'Films', type: 'movies', description: null, role, owner: { id: 1, username: 'owner', display_name: null } })
  vi.mocked(collectionsApi.listMembers).mockResolvedValue([])
  await router.push('/collections/1/settings')
  const wrapper = mount(CollectionSettingsView, { global: { plugins: [createPinia(), router] } })
  await flushPromises()
  return wrapper
}

afterEach(() => vi.clearAllMocks())

describe('CollectionSettingsView', () => {
  it.each(['owner', 'admin', 'editor'] as const)('offers %s an advanced catalog entry point', async (role) => {
    const wrapper = await view(role)

    const advanced = wrapper.findAll('button').find((button) => button.text() === 'Advanced')
    if (!advanced) throw new Error('Advanced settings entry was not found')
    await advanced.trigger('click')
    await flushPromises()
    const advancedLink = wrapper.get('a.button-link')
    expect(advancedLink.text()).toBe('Open advanced catalog')
    expect(advancedLink.attributes('href')).toBe('/collections/1/catalog')
  })

  it('keeps viewers out of the advanced settings section', async () => {
    const wrapper = await view('viewer')

    expect(wrapper.findAll('button').map((button) => button.text())).not.toContain('Advanced')
    expect(wrapper.find('#advanced-catalog-heading').exists()).toBe(false)
  })

  it('uses the consistent three-item primary collection subnavigation', async () => {
    const wrapper = await view('owner')

    expect(wrapper.get('[aria-label="Collection navigation"]').findAll('a').map((link) => link.text())).toEqual(['Inventory', 'Locations', 'Settings'])
  })
})
