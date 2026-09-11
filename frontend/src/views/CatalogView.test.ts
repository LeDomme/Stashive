import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import * as catalogApi from '@/api/catalog'
import * as collectionsApi from '@/api/collections'
import CatalogView from './CatalogView.vue'

vi.mock('@/api/catalog')
vi.mock('@/api/collections')

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/collections/:collectionId/catalog', name: 'catalog', component: CatalogView },
    { path: '/collections/:collectionId/catalog/:entryId', name: 'catalog-detail', component: CatalogView },
    { path: '/collections/:collectionId/inventory', name: 'inventory', component: CatalogView },
    { path: '/collections/:collectionId/locations', name: 'locations', component: CatalogView },
    { path: '/collections/:collectionId/settings', name: 'collection-settings', component: CatalogView },
  ],
})

async function view() {
  vi.mocked(collectionsApi.getCollection).mockResolvedValue({ id: 1, name: 'Films', type: 'movies', description: null, role: 'owner', owner: { id: 1, username: 'owner', display_name: null } })
  vi.mocked(catalogApi.listCatalog).mockResolvedValue([])
  await router.push('/collections/1/catalog')
  const wrapper = mount(CatalogView, { global: { plugins: [createPinia(), router] } })
  await flushPromises()
  return wrapper
}

afterEach(() => vi.clearAllMocks())

describe('CatalogView', () => {
  it('labels the preserved catalog route as advanced and keeps only the normal collection subnavigation', async () => {
    const wrapper = await view()

    expect(wrapper.get('h1').text()).toBe('Advanced catalog')
    expect(wrapper.text()).toContain('For normal collection management, use Inventory.')
    expect(wrapper.get('[aria-label="Collection navigation"]').findAll('a').map((link) => link.text())).toEqual(['Inventory', 'Locations', 'Settings'])
  })
})
