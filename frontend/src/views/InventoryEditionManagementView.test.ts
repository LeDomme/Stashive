import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/api/client'
import * as catalogApi from '@/api/catalog'
import * as collectionsApi from '@/api/collections'
import * as libraryApi from '@/api/library'
import InventoryEditionManagementView from './InventoryEditionManagementView.vue'

vi.mock('@/api/catalog'); vi.mock('@/api/collections'); vi.mock('@/api/library')
const router = createRouter({ history: createMemoryHistory(), routes: [
  { path: '/collections/:collectionId/inventory', name: 'inventory', component: InventoryEditionManagementView },
  { path: '/collections/:collectionId/inventory/:catalogEntryId', name: 'inventory-title', component: InventoryEditionManagementView },
  { path: '/collections/:collectionId/inventory/:catalogEntryId/editions/new', name: 'inventory-edition-new', component: InventoryEditionManagementView },
  { path: '/collections/:collectionId/inventory/:catalogEntryId/editions/:editionId/edit', name: 'inventory-edition-edit', component: InventoryEditionManagementView },
] })
const edition = { id: 4, catalog_entry_id: 3, display_name: 'Special Edition', media_format: 'Blu-ray', release_date: '2003-01-01', publisher: 'Fox', region: 'B', language: 'English', identifiers: [{ id: 5, edition_id: 4, type: 'EAN', value: '123', source: 'manual' }], copies: [] }
const detail = { catalog_entry: { id: 3, collection_id: 2, display_title: 'Alien', type: 'movie', sort_title: null, notes: null }, editions: [edition] }
async function view(path = '/collections/2/inventory/3/editions/4/edit', role: 'editor' | 'viewer' = 'editor') {
  vi.mocked(collectionsApi.getCollection).mockResolvedValue({ id: 2, name: 'Films', type: 'movies', description: null, role, owner: { id: 1, username: 'owner', display_name: null } })
  vi.mocked(libraryApi.getLibraryTitle).mockResolvedValue(detail)
  vi.mocked(libraryApi.listLibrary).mockResolvedValue([])
  await router.push(path)
  const wrapper = mount(InventoryEditionManagementView, { global: { plugins: [createPinia(), router] } })
  await flushPromises()
  return wrapper
}
const button = (wrapper: ReturnType<typeof mount>, name: string) => wrapper.findAll('button').find((candidate) => candidate.text().includes(name))
afterEach(() => vi.clearAllMocks())

describe('InventoryEditionManagementView', () => {
  it('edits existing values with null semantics and refreshes the detail', async () => {
    vi.mocked(catalogApi.updateEdition).mockResolvedValue({ ...edition, publisher: null, region: null, language: null, media_format: null, release_date: null })
    const wrapper = await view()
    expect(wrapper.get('input').element.value).toBe('Special Edition')
    const inputs = wrapper.findAll('input')
    await inputs[1].setValue(''); await inputs[2].setValue(''); await inputs[3].setValue(''); await inputs[4].setValue(''); await inputs[5].setValue('')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(catalogApi.updateEdition).toHaveBeenCalledWith(2, 4, { display_name: 'Special Edition', media_format: null, release_date: null, publisher: null, region: null, language: null })
    expect(router.currentRoute.value.name).toBe('inventory-title')
  })
  it('creates an edition from its dedicated route and supports cancel', async () => {
    vi.mocked(catalogApi.createEdition).mockResolvedValue({ ...edition, id: 9 })
    const wrapper = await view('/collections/2/inventory/3/editions/new')
    await wrapper.get('input').setValue('New edition')
    await wrapper.findAll('input')[1].setValue('DVD')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(catalogApi.createEdition).toHaveBeenCalledWith(2, 3, expect.objectContaining({ display_name: 'New edition', media_format: 'DVD' }))
    expect(router.currentRoute.value.name).toBe('inventory-title')
  })
  it('manages barcodes and IDs with duplicate feedback and confirmed deletion', async () => {
    const wrapper = await view()
    await button(wrapper, 'Barcodes & IDs')?.trigger('click')
    expect(wrapper.text()).toContain('EAN')
    await button(wrapper, 'Add barcode or ID')?.trigger('click')
    const fields = wrapper.findAll('input'); await fields[0].setValue('EAN'); await fields[1].setValue('123')
    vi.mocked(catalogApi.createIdentifier).mockRejectedValue(new ApiError(409))
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('already exists')
    await button(wrapper, 'Delete')?.trigger('click')
    expect(catalogApi.deleteIdentifier).not.toHaveBeenCalled()
    vi.mocked(catalogApi.deleteIdentifier).mockResolvedValue()
    await button(wrapper, 'Confirm delete')?.trigger('click'); await flushPromises()
    expect(catalogApi.deleteIdentifier).toHaveBeenCalledWith(2, 4, 5)
  })
  it('deletes editions only from the danger zone and keeps viewers read-only', async () => {
    vi.mocked(catalogApi.deleteEdition).mockResolvedValue()
    const wrapper = await view()
    await button(wrapper, 'Danger zone')?.trigger('click'); await button(wrapper, 'Delete edition')?.trigger('click')
    expect(catalogApi.deleteEdition).not.toHaveBeenCalled()
    await button(wrapper, 'Confirm delete edition')?.trigger('click'); await flushPromises()
    expect(catalogApi.deleteEdition).toHaveBeenCalledWith(2, 4)
    expect(router.currentRoute.value.name).toBe('inventory-title')
    const viewer = await view(undefined, 'viewer')
    expect(viewer.text()).toContain('do not have permission')
    expect(viewer.find('form').exists()).toBe(false)
  })
})
