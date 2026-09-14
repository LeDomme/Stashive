import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as catalogApi from '@/api/catalog'
import * as collectionsApi from '@/api/collections'
import * as libraryApi from '@/api/library'
import InventoryTitleManagementView from './InventoryTitleManagementView.vue'

vi.mock('@/api/catalog'); vi.mock('@/api/collections'); vi.mock('@/api/library')
const router = createRouter({ history: createMemoryHistory(), routes: [
  { path: '/collections/:collectionId/inventory', name: 'inventory', component: InventoryTitleManagementView },
  { path: '/collections/:collectionId/inventory/:catalogEntryId', name: 'inventory-title', component: InventoryTitleManagementView },
  { path: '/collections/:collectionId/inventory/:catalogEntryId/edit', name: 'inventory-title-edit', component: InventoryTitleManagementView },
] })
const entry = { id: 3, collection_id: 2, display_title: 'Alien', type: 'movie', sort_title: 'Alien, The', notes: 'Classic' }
const detail = { catalog_entry: entry, editions: [] }
async function view(role: 'editor' | 'viewer' = 'editor') {
  vi.mocked(collectionsApi.getCollection).mockResolvedValue({ id: 2, name: 'Films', type: 'movies', description: null, role, owner: { id: 1, username: 'owner', display_name: null } })
  vi.mocked(catalogApi.getCatalog).mockResolvedValue(entry)
  vi.mocked(catalogApi.listEditions).mockResolvedValue([])
  vi.mocked(libraryApi.getLibraryTitle).mockResolvedValue(detail)
  vi.mocked(libraryApi.listLibrary).mockResolvedValue([])
  await router.push('/collections/2/inventory/3/edit')
  const wrapper = mount(InventoryTitleManagementView, { global: { plugins: [createPinia(), router] } })
  await flushPromises()
  return wrapper
}
const button = (wrapper: ReturnType<typeof mount>, name: string) => wrapper.findAll('button').find((candidate) => candidate.text().includes(name))
afterEach(() => vi.clearAllMocks())

describe('InventoryTitleManagementView', () => {
  it('loads current title data, saves it and refreshes library state', async () => {
    vi.mocked(catalogApi.updateCatalog).mockResolvedValue({ ...entry, display_title: 'Alien (1979)' })
    const wrapper = await view()
    expect(wrapper.get('input').element.value).toBe('Alien')
    await wrapper.get('input').setValue('Alien (1979)')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(catalogApi.updateCatalog).toHaveBeenCalledWith(2, 3, { display_title: 'Alien (1979)', sort_title: 'Alien, The', type: 'movie', notes: 'Classic' })
    expect(libraryApi.getLibraryTitle).toHaveBeenCalledWith(2, 3)
    expect(libraryApi.listLibrary).toHaveBeenCalledWith(2, {})
    expect(router.currentRoute.value.name).toBe('inventory-title')
  })
  it('cancels without mutation and protects deletion with a confirmation', async () => {
    const wrapper = await view()
    await wrapper.get('.button-secondary.button-link').trigger('click')
    await flushPromises()
    expect(catalogApi.updateCatalog).not.toHaveBeenCalled()
    await router.push('/collections/2/inventory/3/edit')
    const danger = mount(InventoryTitleManagementView, { global: { plugins: [createPinia(), router] } })
    await flushPromises()
    await button(danger, 'Danger zone')?.trigger('click')
    await button(danger, 'Delete title')?.trigger('click')
    expect(catalogApi.deleteCatalog).not.toHaveBeenCalled()
    expect(danger.text()).toContain('Confirm delete title')
  })
  it('deletes through the danger zone and returns to inventory', async () => {
    vi.mocked(catalogApi.deleteCatalog).mockResolvedValue()
    const wrapper = await view()
    await button(wrapper, 'Danger zone')?.trigger('click'); await button(wrapper, 'Delete title')?.trigger('click'); await button(wrapper, 'Confirm delete title')?.trigger('click')
    await flushPromises()
    expect(catalogApi.deleteCatalog).toHaveBeenCalledWith(2, 3)
    expect(router.currentRoute.value.name).toBe('inventory')
  })
  it('does not render management forms for viewers', async () => {
    const wrapper = await view('viewer')
    expect(wrapper.text()).toContain('do not have permission')
    expect(wrapper.find('form').exists()).toBe(false)
  })
})
