import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as collectionsApi from '@/api/collections'
import * as libraryApi from '@/api/library'
import * as locationsApi from '@/api/locations'
import InventoryAddCopyView from './InventoryAddCopyView.vue'

vi.mock('@/api/collections'); vi.mock('@/api/library'); vi.mock('@/api/locations')
const router = createRouter({ history: createMemoryHistory(), routes: [
  { path: '/collections/:collectionId/inventory/:catalogEntryId', name: 'inventory-title', component: InventoryAddCopyView },
  { path: '/collections/:collectionId/inventory/:catalogEntryId/editions/:editionId/copies/new', name: 'inventory-copy-new', component: InventoryAddCopyView },
] })
const detail = { catalog_entry: { id: 3, collection_id: 2, display_title: 'Alien', type: 'movie', sort_title: null, notes: null }, editions: [{ id: 4, catalog_entry_id: 3, display_name: 'Special Edition', media_format: 'Blu-ray', release_date: null, publisher: null, regions: [], languages: [], identifiers: [], copies: [{ id: 5, edition_id: 4, condition: 'Mint', notes: null, location_id: null, created_at: '2026-01-01T00:00:00', updated_at: '2026-01-01T00:00:00' }] }] }
async function view(role: 'editor' | 'viewer' = 'editor', response = detail) {
  vi.mocked(collectionsApi.getCollection).mockResolvedValue({ id: 2, name: 'Films', type: 'movies', description: null, role, owner: { id: 1, username: 'owner', display_name: null } })
  vi.mocked(libraryApi.getLibraryTitle).mockResolvedValue(response)
  vi.mocked(libraryApi.listLibrary).mockResolvedValue([])
  vi.mocked(locationsApi.listLocationTree).mockResolvedValue([{ id: 7, collection_id: 2, parent_id: null, name: 'Archive', type: 'room', description: null, children: [] }])
  await router.push('/collections/2/inventory/3/editions/4/copies/new')
  const wrapper = mount(InventoryAddCopyView, { global: { plugins: [createPinia(), router] } })
  await flushPromises()
  return wrapper
}
afterEach(() => vi.clearAllMocks())

describe('InventoryAddCopyView', () => {
  it('uses case C for an existing title and edition, then returns to the detail', async () => {
    vi.mocked(libraryApi.addItem).mockResolvedValue({ catalog_entry_id: 3, edition_id: 4, inventory_item_id: 6 })
    const wrapper = await view()
    expect(wrapper.text()).toContain('Alien · Special Edition · Blu-ray')
    expect(wrapper.text()).not.toContain('Publisher / distributor')
    await wrapper.get('#copy-condition').setValue('Sealed')
    await wrapper.findAll('select')[1].setValue('7')
    await wrapper.get('textarea').setValue('Second disc')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(libraryApi.addItem).toHaveBeenCalledWith(2, { title: { existing_id: 3, new: null }, edition: { existing_id: 4, new: null }, copy: { condition: 'Sealed', notes: 'Second disc', location_id: 7 } })
    expect(router.currentRoute.value.name).toBe('inventory-title')
  })
  it('keeps the copy fields available after a safe error', async () => {
    vi.mocked(libraryApi.addItem).mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ catalog_entry_id: 3, edition_id: 4, inventory_item_id: 6 })
    const wrapper = await view()
    await wrapper.get('#copy-condition').setValue('Mint')
    await wrapper.get('textarea').setValue('Keep upright')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('could not be added')
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('Keep upright')
  })
  it('keeps viewers read-only and reports an edition outside the title as unavailable', async () => {
    const viewer = await view('viewer')
    expect(viewer.text()).toContain('do not have permission')
    expect(viewer.find('form').exists()).toBe(false)
    const missing = await view('editor', { ...detail, editions: [] })
    expect(missing.text()).toContain('This edition is not available.')
  })
})
