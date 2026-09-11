import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as collectionsApi from '@/api/collections'
import * as inventoryApi from '@/api/inventory'
import * as libraryApi from '@/api/library'
import * as locationsApi from '@/api/locations'
import InventoryCopyManagementView from './InventoryCopyManagementView.vue'

vi.mock('@/api/collections'); vi.mock('@/api/inventory'); vi.mock('@/api/library'); vi.mock('@/api/locations')
const router = createRouter({ history: createMemoryHistory(), routes: [
  { path: '/collections/:collectionId/inventory', name: 'inventory', component: InventoryCopyManagementView },
  { path: '/collections/:collectionId/inventory/:catalogEntryId', name: 'inventory-title', component: InventoryCopyManagementView },
  { path: '/collections/:collectionId/inventory/:catalogEntryId/editions/:editionId/copies/:inventoryItemId/edit', name: 'inventory-copy-edit', component: InventoryCopyManagementView },
] })
const locations = [{ id: 1, collection_id: 2, parent_id: null, name: 'House', type: 'room' as const, description: null, children: [{ id: 2, collection_id: 2, parent_id: 1, name: 'Basement', type: 'room' as const, description: null, children: [{ id: 3, collection_id: 2, parent_id: 2, name: 'Shelf', type: 'shelf' as const, description: null, children: [] }] }, { id: 4, collection_id: 2, parent_id: 1, name: 'Office', type: 'room' as const, description: null, children: [{ id: 5, collection_id: 2, parent_id: 4, name: 'Shelf', type: 'shelf' as const, description: null, children: [] }] }] }]
const first = { id: 6, edition_id: 4, condition: 'Good', notes: 'First copy', location_id: 3, created_at: '2026-01-01T00:00:00', updated_at: '2026-01-01T00:00:00' }
const second = { id: 7, edition_id: 4, condition: null, notes: null, location_id: null, created_at: '2026-01-02T00:00:00', updated_at: '2026-01-02T00:00:00' }
const detail = { catalog_entry: { id: 3, collection_id: 2, display_title: 'Alien', type: 'movie', sort_title: null, notes: null }, editions: [{ id: 4, catalog_entry_id: 3, display_name: 'Special Edition', media_format: 'Blu-ray', release_date: null, publisher: null, region: null, language: null, identifiers: [], copies: [first, second] }, { id: 8, catalog_entry_id: 3, display_name: 'Other', media_format: null, release_date: null, publisher: null, region: null, language: null, identifiers: [], copies: [{ ...first, id: 9, edition_id: 8 }] }] }
async function view(path = '/collections/2/inventory/3/editions/4/copies/7/edit', role: 'editor' | 'viewer' = 'editor', response = detail) {
  vi.mocked(collectionsApi.getCollection).mockResolvedValue({ id: 2, name: 'Films', type: 'movies', description: null, role, owner: { id: 1, username: 'owner', display_name: null } })
  vi.mocked(libraryApi.getLibraryTitle).mockResolvedValue(response)
  vi.mocked(libraryApi.listLibrary).mockResolvedValue([])
  vi.mocked(locationsApi.listLocationTree).mockResolvedValue(locations)
  await router.push(path)
  const wrapper = mount(InventoryCopyManagementView, { global: { plugins: [createPinia(), router] } })
  await flushPromises()
  return wrapper
}
const button = (wrapper: ReturnType<typeof mount>, name: string) => wrapper.findAll('button').find((candidate) => candidate.text().includes(name))
afterEach(() => vi.clearAllMocks())

describe('InventoryCopyManagementView', () => {
  it('loads a hierarchically scoped copy as the same deterministic copy number', async () => {
    const wrapper = await view()
    expect(libraryApi.getLibraryTitle).toHaveBeenCalledWith(2, 3)
    expect(wrapper.text()).toContain('Alien')
    expect(wrapper.text()).toContain('Special Edition · Blu-ray')
    expect(wrapper.get('h1').text()).toBe('Copy 2')
    expect(wrapper.get('select').element.value).toBe('')
    expect(wrapper.get('textarea').element.value).toBe('')
  })
  it('saves only the selected copy with null semantics and refreshes library state', async () => {
    vi.mocked(inventoryApi.updateInventoryItem).mockResolvedValue({ ...second, condition: null, notes: null })
    const wrapper = await view()
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(inventoryApi.updateInventoryItem).toHaveBeenCalledWith(2, 7, { condition: null, notes: null })
    expect(inventoryApi.updateInventoryItem).not.toHaveBeenCalledWith(2, 6, expect.anything())
    expect(libraryApi.getLibraryTitle).toHaveBeenCalledWith(2, 3)
    expect(libraryApi.listLibrary).toHaveBeenCalledWith(2, {})
    expect(router.currentRoute.value.name).toBe('inventory-title')
  })
  it('selects and saves a known condition preset', async () => {
    vi.mocked(inventoryApi.updateInventoryItem).mockResolvedValue(first)
    const wrapper = await view('/collections/2/inventory/3/editions/4/copies/6/edit')
    expect((wrapper.get('#copy-condition').element as HTMLSelectElement).value).toBe('Good')
    await wrapper.get('#copy-condition').setValue('Very Good')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(inventoryApi.updateInventoryItem).toHaveBeenCalledWith(2, 6, { condition: 'Very Good', notes: 'First copy' })
  })
  it('shows and preserves an unknown custom condition', async () => {
    const sealed = { ...second, condition: 'Sealed' }
    vi.mocked(inventoryApi.updateInventoryItem).mockResolvedValue(sealed)
    const wrapper = await view(undefined, 'editor', { ...detail, editions: [{ ...detail.editions[0], copies: [first, sealed] }, detail.editions[1]] })
    expect((wrapper.get('#copy-condition').element as HTMLSelectElement).value).toBe('__custom__')
    expect((wrapper.get('#copy-condition-custom').element as HTMLInputElement).value).toBe('Sealed')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(inventoryApi.updateInventoryItem).toHaveBeenCalledWith(2, 7, { condition: 'Sealed', notes: null })
  })
  it('cancels general editing without mutation', async () => {
    const wrapper = await view()
    await wrapper.get('.button-secondary.button-link').trigger('click'); await flushPromises()
    expect(inventoryApi.updateInventoryItem).not.toHaveBeenCalled()
    expect(router.currentRoute.value.name).toBe('inventory-title')
  })
  it('assigns, moves and unassigns using complete nested location paths', async () => {
    vi.mocked(inventoryApi.updateInventoryItem).mockResolvedValue({ ...second, location_id: 5 })
    const wrapper = await view()
    await button(wrapper, 'Location')?.trigger('click')
    expect(wrapper.text()).toContain('Current location')
    expect(wrapper.text()).toContain('Unassigned')
    const select = wrapper.get('select')
    expect(select.text()).toContain('House > Basement > Shelf')
    expect(select.text()).toContain('House > Office > Shelf')
    vi.mocked(libraryApi.getLibraryTitle).mockResolvedValueOnce({ ...detail, editions: [{ ...detail.editions[0], copies: [first, { ...second, location_id: 5 }] }, detail.editions[1]] })
    await select.setValue('5'); await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(inventoryApi.updateInventoryItem).toHaveBeenCalledWith(2, 7, { location_id: 5 })
    vi.mocked(inventoryApi.updateInventoryItem).mockResolvedValue({ ...second, location_id: null })
    await button(wrapper, 'Remove from location')?.trigger('click'); await flushPromises()
    expect(inventoryApi.updateInventoryItem).toHaveBeenLastCalledWith(2, 7, { location_id: null })
  })
  it('confirms deletion of only the selected physical copy and returns to title detail', async () => {
    vi.mocked(inventoryApi.deleteInventoryItem).mockResolvedValue()
    const wrapper = await view()
    await button(wrapper, 'Danger zone')?.trigger('click'); await button(wrapper, 'Delete physical copy')?.trigger('click')
    expect(inventoryApi.deleteInventoryItem).not.toHaveBeenCalled()
    await button(wrapper, 'Cancel')?.trigger('click')
    expect(inventoryApi.deleteInventoryItem).not.toHaveBeenCalled()
    await button(wrapper, 'Delete physical copy')?.trigger('click'); await button(wrapper, 'Confirm delete physical copy')?.trigger('click'); await flushPromises()
    expect(inventoryApi.deleteInventoryItem).toHaveBeenCalledWith(2, 7)
    expect(inventoryApi.deleteInventoryItem).not.toHaveBeenCalledWith(2, 6)
    expect(router.currentRoute.value.name).toBe('inventory-title')
  })
  it('rejects mismatched edition or copy routes and keeps viewers read-only', async () => {
    const wrongEdition = await view('/collections/2/inventory/3/editions/8/copies/7/edit')
    expect(wrongEdition.get('[role="alert"]').text()).toContain('not available')
    expect(wrongEdition.find('form').exists()).toBe(false)
    const wrongCopy = await view('/collections/2/inventory/3/editions/4/copies/9/edit')
    expect(wrongCopy.get('[role="alert"]').text()).toContain('not available')
    const viewer = await view(undefined, 'viewer')
    expect(viewer.text()).toContain('do not have permission')
    expect(viewer.find('form').exists()).toBe(false)
  })
})
