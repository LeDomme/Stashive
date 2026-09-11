import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as collectionsApi from '@/api/collections'
import * as libraryApi from '@/api/library'
import * as locationsApi from '@/api/locations'
import InventoryTitlePlaceholderView from './InventoryTitlePlaceholderView.vue'

vi.mock('@/api/collections'); vi.mock('@/api/library'); vi.mock('@/api/locations')
const router = createRouter({ history: createMemoryHistory(), routes: [
  { path: '/collections/:collectionId/inventory', name: 'inventory', component: InventoryTitlePlaceholderView },
  { path: '/collections/:collectionId/inventory/:catalogEntryId', name: 'inventory-title', component: InventoryTitlePlaceholderView },
  { path: '/collections/:collectionId/inventory/:catalogEntryId/edit', name: 'inventory-title-edit', component: InventoryTitlePlaceholderView },
  { path: '/collections/:collectionId/inventory/:catalogEntryId/editions/new', name: 'inventory-edition-new', component: InventoryTitlePlaceholderView },
  { path: '/collections/:collectionId/inventory/:catalogEntryId/editions/:editionId/edit', name: 'inventory-edition-edit', component: InventoryTitlePlaceholderView },
] })
const locations = [{ id: 1, collection_id: 2, parent_id: null, name: 'House', type: 'room' as const, description: null, children: [{ id: 2, collection_id: 2, parent_id: 1, name: 'Basement', type: 'room' as const, description: null, children: [{ id: 3, collection_id: 2, parent_id: 2, name: 'Box', type: 'box' as const, description: null, children: [] }] }] }]
const detail = {
  catalog_entry: { id: 3, collection_id: 2, display_title: 'Alien', type: 'movie', sort_title: 'Alien, The', notes: 'A classic.' },
  editions: [
    { id: 4, catalog_entry_id: 3, display_name: 'Special Edition', media_format: 'Blu-ray', release_date: '2003-01-01', publisher: 'Fox', region: 'B', language: 'English', identifiers: [{ id: 5, edition_id: 4, type: 'EAN', value: '123', source: 'manual' }], copies: [
      { id: 7, edition_id: 4, condition: 'Very good', notes: 'Keep upright', location_id: 3, created_at: '2026-01-02T00:00:00', updated_at: '2026-01-02T00:00:00' },
      { id: 6, edition_id: 4, condition: null, notes: null, location_id: null, created_at: '2026-01-01T00:00:00', updated_at: '2026-01-01T00:00:00' },
    ] },
    { id: 8, catalog_entry_id: 3, display_name: 'Director’s Cut', media_format: 'UHD Blu-ray', release_date: null, publisher: null, region: null, language: null, identifiers: [], copies: [] },
  ],
}
async function view(response = detail, role: 'editor' | 'viewer' = 'viewer') {
  vi.mocked(collectionsApi.getCollection).mockResolvedValue({ id: 2, name: 'Films', type: 'movies', description: null, role, owner: { id: 1, username: 'owner', display_name: null } })
  vi.mocked(locationsApi.listLocationTree).mockResolvedValue(locations)
  vi.mocked(libraryApi.getLibraryTitle).mockResolvedValue(response)
  await router.push('/collections/2/inventory/3')
  const wrapper = mount(InventoryTitlePlaceholderView, { global: { plugins: [createPinia(), router] } })
  await flushPromises()
  return wrapper
}
afterEach(() => vi.clearAllMocks())

describe('InventoryTitlePlaceholderView', () => {
  it('loads the title detail through the library store and renders title metadata and its cover placeholder', async () => {
    const wrapper = await view()
    expect(libraryApi.getLibraryTitle).toHaveBeenCalledWith(2, 3)
    expect(wrapper.text()).toContain('Films · Inventory')
    expect(wrapper.get('h1').text()).toBe('Alien')
    expect(wrapper.text()).toContain('Sort title: Alien, The')
    expect(wrapper.text()).toContain('Movie')
    expect(wrapper.text()).toContain('A classic.')
    expect(wrapper.get('.inventory-title-detail__cover').text()).toBe('Stashive')
  })
  it('renders editions, format badges, metadata and barcode details without management controls', async () => {
    const wrapper = await view()
    expect(wrapper.findAll('.edition-detail-card')).toHaveLength(2)
    expect(wrapper.text()).toContain('Special Edition')
    expect(wrapper.get('.edition-format-badge').text()).toBe('Blu-ray')
    expect(wrapper.text()).toContain('2003-01-01 · Region B · English')
    expect(wrapper.text()).toContain('Fox')
    expect(wrapper.text()).toContain('Barcodes & IDs')
    expect(wrapper.text()).toContain('EAN')
    expect(wrapper.text()).toContain('123')
    expect(wrapper.text()).toContain('manual')
    expect(wrapper.text()).not.toContain('Add Barcode')
    expect(wrapper.text()).not.toContain('Edit copy')
  })
  it('renders deterministic copies with paths, unassigned state, condition and notes', async () => {
    const wrapper = await view()
    const copies = wrapper.findAll('.copy-read-card')
    expect(copies).toHaveLength(2)
    expect(copies[0].text()).toContain('Copy 1')
    expect(copies[0].text()).toContain('Unassigned')
    expect(copies[1].text()).toContain('Copy 2')
    expect(copies[1].text()).toContain('House > Basement > Box')
    expect(copies[1].text()).toContain('Very good')
    expect(copies[1].text()).toContain('Keep upright')
  })
  it('renders neutral nested empty states', async () => {
    const wrapper = await view()
    expect(wrapper.text()).toContain('No barcodes or IDs.')
    expect(wrapper.text()).toContain('No physical copies.')
    const noEditions = await view({ ...detail, editions: [] })
    expect(noEditions.text()).toContain('No editions')
  })
  it('navigates back to the collection inventory route', async () => {
    const wrapper = await view()
    await wrapper.get('.back-link').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('inventory')
    expect(router.currentRoute.value.params.collectionId).toBe('2')
  })
  it('shows title and edition management entry points only to content editors', async () => {
    const editor = await view(detail, 'editor')
    expect(editor.text()).toContain('Edit title')
    expect(editor.text()).toContain('Add edition')
    expect(editor.text()).toContain('Edit edition')
    const viewer = await view()
    expect(viewer.text()).not.toContain('Edit title')
    expect(viewer.text()).not.toContain('Add edition')
    expect(viewer.text()).not.toContain('Edit edition')
  })
})
