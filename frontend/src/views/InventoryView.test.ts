import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as catalogApi from '@/api/catalog'
import * as collectionsApi from '@/api/collections'
import * as inventoryApi from '@/api/inventory'
import * as libraryApi from '@/api/library'
import * as locationsApi from '@/api/locations'
import InventoryView from './InventoryView.vue'

vi.mock('@/api/catalog'); vi.mock('@/api/collections'); vi.mock('@/api/inventory'); vi.mock('@/api/library'); vi.mock('@/api/locations')
const router = createRouter({ history: createMemoryHistory(), routes: [
  { path: '/collections/:collectionId/inventory', name: 'inventory', component: InventoryView },
  { path: '/collections/:collectionId/inventory/:catalogEntryId', name: 'inventory-title', component: InventoryView },
  { path: '/collections/:collectionId/catalog', name: 'catalog', component: InventoryView },
  { path: '/collections/:collectionId/locations', name: 'locations', component: InventoryView },
  { path: '/collections/:collectionId/settings', name: 'collection-settings', component: InventoryView },
] })
const entry = { id: 2, collection_id: 1, display_title: 'Blade Runner', type: 'movie', sort_title: null, notes: null }
const edition = { id: 3, catalog_entry_id: 2, display_name: 'UHD Blu-ray', media_format: 'UHD Blu-ray', release_date: null, publisher: null, region: null, language: null }
const titles = [
  { id: 2, catalog_entry_id: 2, display_title: 'Blade Runner', sort_title: null, type: 'movie', edition_count: 2, copy_count: 3, media_formats: ['Blu-ray', 'UHD Blu-ray'] },
  { id: 5, catalog_entry_id: 5, display_title: 'Heat', sort_title: null, type: 'movie', edition_count: 1, copy_count: 0, media_formats: [] },
]
const tree = [{ id: 7, collection_id: 1, parent_id: null, name: 'House', type: 'room' as const, description: null, children: [{ id: 8, collection_id: 1, parent_id: 7, name: 'Shelf', type: 'shelf' as const, description: null, children: [] }] }]

async function view(role: 'owner' | 'admin' | 'editor' | 'viewer' = 'owner', summaries = titles) {
  vi.mocked(collectionsApi.getCollection).mockResolvedValue({ id: 1, name: 'Films', type: 'movies', description: null, role, owner: { id: 1, username: 'owner', display_name: null } })
  vi.mocked(libraryApi.listLibrary).mockResolvedValue(summaries)
  vi.mocked(catalogApi.listCatalog).mockResolvedValue([entry])
  vi.mocked(catalogApi.listEditions).mockResolvedValue([edition])
  vi.mocked(locationsApi.listLocationTree).mockResolvedValue(tree)
  await router.push('/collections/1/inventory')
  const wrapper = mount(InventoryView, { global: { plugins: [createPinia(), router] } })
  await flushPromises()
  return wrapper
}
function button(wrapper: VueWrapper, name: string) { return wrapper.findAll('button').find((candidate) => candidate.text() === name) }
function input(wrapper: VueWrapper, label: string) { const field = wrapper.findAll('label').find((candidate) => candidate.text().startsWith(label)); if (!field) throw new Error(label); return field.get('input, textarea, select') }
function form(wrapper: VueWrapper, text: string) { const found = wrapper.findAll('form').find((candidate) => candidate.text().includes(text)); if (!found) throw new Error(text); return found }
afterEach(() => vi.clearAllMocks())

describe('InventoryView', () => {
  it('renders one title card per catalog entry with counts, formats and a cover placeholder', async () => {
    const wrapper = await view()
    expect(wrapper.findAll('.library-card')).toHaveLength(2)
    expect(wrapper.get('.library-card').text()).toContain('2 editions · 3 copies')
    expect(wrapper.get('.library-card').text()).toContain('Blu-ray · UHD Blu-ray')
    expect(wrapper.get('.library-card__cover').text()).toBe('Stashive')
    expect(wrapper.find('.inventory-list').exists()).toBe(false)
  })
  it('renders singular result and card counts', async () => {
    const wrapper = await view('viewer', [{ ...titles[0], edition_count: 1, copy_count: 1, media_formats: [] }])
    expect(wrapper.get('.filter-toolbar__summary').text()).toBe('1 title · 1 physical copy')
    expect(wrapper.get('.library-card__summary').text()).toBe('1 edition · 1 copy')
  })
  it('shows Add item for every content editor role and never for viewers', async () => {
    for (const role of ['owner', 'admin', 'editor'] as const) expect(button(await view(role), 'Add item')).toBeDefined()
    expect(button(await view('viewer'), 'Add item')).toBeUndefined()
  })
  it('uses the existing physical-copy form from Add item and refreshes the library summary', async () => {
    vi.mocked(inventoryApi.createInventoryItem).mockResolvedValue({ id: 4, edition_id: 3, condition: null, notes: null, location_id: null, created_at: '2026-01-01T00:00:00', updated_at: '2026-01-01T00:00:00' })
    const wrapper = await view()
    await button(wrapper, 'Add item')?.trigger('click')
    await input(wrapper, 'Edition').setValue('3')
    await form(wrapper, 'Create physical copy').trigger('submit')
    await flushPromises()
    expect(inventoryApi.createInventoryItem).toHaveBeenCalledWith(1, { edition_id: 3, condition: null, notes: null })
    expect(libraryApi.listLibrary).toHaveBeenLastCalledWith(1, {})
  })
  it('shows role-aware empty states', async () => {
    expect((await view('owner', [])).text()).toContain('No titles yet')
    expect(button(await view('owner', []), 'Add item')).toBeDefined()
    expect(button(await view('viewer', []), 'Add item')).toBeUndefined()
  })
  it('sends all, unassigned, recursive and exact filters to the library read model', async () => {
    const wrapper = await view('viewer')
    await form(wrapper, 'Apply filter').trigger('submit'); await flushPromises()
    expect(libraryApi.listLibrary).toHaveBeenLastCalledWith(1, {})
    await input(wrapper, 'Filter').setValue('unassigned'); await form(wrapper, 'Apply filter').trigger('submit'); await flushPromises()
    expect(libraryApi.listLibrary).toHaveBeenLastCalledWith(1, { unassigned: true })
    await input(wrapper, 'Filter').setValue('location'); await input(wrapper, 'Location').setValue('7'); await form(wrapper, 'Apply filter').trigger('submit'); await flushPromises()
    expect(libraryApi.listLibrary).toHaveBeenLastCalledWith(1, { locationId: 7, includeDescendants: true })
    await wrapper.get('input[type="checkbox"]').setValue(false); await form(wrapper, 'Apply filter').trigger('submit'); await flushPromises()
    expect(libraryApi.listLibrary).toHaveBeenLastCalledWith(1, { locationId: 7, includeDescendants: false })
  })
  it('clears filters and restores the unfiltered title list', async () => {
    const wrapper = await view('viewer')
    await input(wrapper, 'Filter').setValue('location'); await input(wrapper, 'Location').setValue('7'); await button(wrapper, 'Clear')?.trigger('click'); await flushPromises()
    expect(input(wrapper, 'Filter').element.value).toBe('all')
    expect(libraryApi.listLibrary).toHaveBeenLastCalledWith(1, {})
  })
})
