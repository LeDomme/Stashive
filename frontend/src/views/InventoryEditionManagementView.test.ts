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
const edition = { id: 4, catalog_entry_id: 3, display_name: 'Special Edition', media_format: 'Blu-ray', release_date: '2003-01-01', publisher: 'Fox', regions: ['B'], languages: ['English'], identifiers: [{ id: 5, edition_id: 4, type: 'EAN', value: '123', source: 'manual' }], copies: [] }
const detail = { catalog_entry: { id: 3, collection_id: 2, display_title: 'Alien', type: 'movie', sort_title: null, notes: null }, editions: [edition] }
async function view(path = '/collections/2/inventory/3/editions/4/edit', role: 'editor' | 'viewer' = 'editor', response = detail, collectionType = 'movies') {
  vi.mocked(collectionsApi.getCollection).mockResolvedValue({ id: 2, name: 'Films', type: collectionType, description: null, role, owner: { id: 1, username: 'owner', display_name: null } })
  vi.mocked(libraryApi.getLibraryTitle).mockResolvedValue(response)
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
    vi.mocked(catalogApi.updateEdition).mockResolvedValue({ ...edition, publisher: null, regions: [], languages: [], media_format: null, release_date: null })
    const wrapper = await view()
    expect((wrapper.get('#edition-name').element as HTMLSelectElement).value).toBe('Special Edition')
    await wrapper.get('#edition-format').setValue('')
    await wrapper.get('input[type="date"]').setValue('')
    await wrapper.get('#publisher').setValue('')
    await wrapper.get('#languages').trigger('click')
    await wrapper.get('[aria-label="Remove English"]').trigger('click')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(catalogApi.updateEdition).toHaveBeenCalledWith(2, 4, { display_name: 'Special Edition', media_format: null, release_date: null, publisher: null, regions: ['B'], languages: [] })
    expect(router.currentRoute.value.name).toBe('inventory-title')
  })
  it('adds an edition and its first copy through the transactional add-item flow', async () => {
    vi.mocked(libraryApi.addItem).mockResolvedValue({ catalog_entry_id: 3, edition_id: 9, inventory_item_id: 10 })
    const wrapper = await view('/collections/2/inventory/3/editions/new')
    await wrapper.findAll('select')[0].setValue('__custom__')
    await wrapper.get('input').setValue('New edition')
    await wrapper.findAll('select')[1].setValue('Blu-ray')
    await wrapper.findAll('select')[2].setValue('Warner Bros. Home Entertainment')
    await wrapper.get('#regions').trigger('click')
    await wrapper.findAll('#regions-popover input[type="checkbox"]')[1].setValue(true)
    await wrapper.get('#languages').trigger('click')
    const choices = wrapper.findAll('#languages-popover input[type="checkbox"]')
    await choices[0].setValue(true); await choices[1].setValue(true)
    await wrapper.findAll('select')[3].setValue('Sealed')
    await wrapper.get('textarea').setValue('First copy')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(libraryApi.addItem).toHaveBeenCalledWith(2, expect.objectContaining({ title: { existing_id: 3, new: null }, edition: expect.objectContaining({ existing_id: null, new: expect.objectContaining({ display_name: 'New edition', media_format: 'Blu-ray', publisher: 'Warner Bros. Home Entertainment', regions: ['Region B'], languages: ['German', 'English'] }) }), copy: { condition: 'Sealed', notes: 'First copy', location_id: null } }))
    expect(router.currentRoute.value.name).toBe('inventory-title')
  })
  it('shows known preset values without custom inputs and preserves them on save', async () => {
    vi.mocked(catalogApi.updateEdition).mockResolvedValue({ ...edition, display_name: 'Steelbook' })
    const wrapper = await view(undefined, 'editor', { ...detail, editions: [{ ...edition, display_name: 'Steelbook' }] })
    expect((wrapper.get('#edition-name').element as HTMLSelectElement).value).toBe('Steelbook')
    expect((wrapper.get('#edition-format').element as HTMLSelectElement).value).toBe('Blu-ray')
    expect(wrapper.find('#edition-name-custom').exists()).toBe(false)
    expect(wrapper.find('#edition-format-custom').exists()).toBe(false)
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(catalogApi.updateEdition).toHaveBeenCalledWith(2, 4, expect.objectContaining({ display_name: 'Steelbook', media_format: 'Blu-ray' }))
  })
  it('shows and preserves unknown custom edition values including existing Box Set data', async () => {
    const custom = { ...edition, display_name: 'Box Set', media_format: 'Video CD' }
    vi.mocked(catalogApi.updateEdition).mockResolvedValue(custom)
    const wrapper = await view(undefined, 'editor', { ...detail, editions: [custom] })
    expect((wrapper.get('#edition-name').element as HTMLSelectElement).value).toBe('__custom__')
    expect((wrapper.get('#edition-name-custom').element as HTMLInputElement).value).toBe('Box Set')
    expect((wrapper.get('#edition-format').element as HTMLSelectElement).value).toBe('__custom__')
    expect((wrapper.get('#edition-format-custom').element as HTMLInputElement).value).toBe('Video CD')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(catalogApi.updateEdition).toHaveBeenCalledWith(2, 4, expect.objectContaining({ display_name: 'Box Set', media_format: 'Video CD' }))
  })
  it('keeps null preset fields empty without a custom input', async () => {
    const empty = { ...edition, display_name: '', media_format: null }
    const wrapper = await view(undefined, 'editor', { ...detail, editions: [empty] })
    expect((wrapper.get('#edition-name').element as HTMLSelectElement).value).toBe('')
    expect((wrapper.get('#edition-format').element as HTMLSelectElement).value).toBe('')
    expect(wrapper.find('#edition-name-custom').exists()).toBe(false)
    expect(wrapper.find('#edition-format-custom').exists()).toBe(false)
  })
  it('hides movie metadata for non-movie collections without overwriting stored values', async () => {
    vi.mocked(catalogApi.updateEdition).mockResolvedValue(edition)
    const wrapper = await view(undefined, 'editor', detail, 'board_games')
    expect(wrapper.text()).not.toContain('Movie metadata')
    expect(wrapper.text()).not.toContain('Publisher / distributor')
    expect(wrapper.find('#regions-custom').exists()).toBe(false)
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(catalogApi.updateEdition).toHaveBeenCalledWith(2, 4, { display_name: 'Special Edition', release_date: '2003-01-01' })
  })
  it('keeps existing regions and asks for review when an edited media format changes', async () => {
    const dvd = { ...edition, media_format: 'DVD', regions: ['Region 2'], languages: ['German', 'Latin'], publisher: 'Custom distributor' }
    vi.mocked(catalogApi.updateEdition).mockResolvedValue(dvd)
    const wrapper = await view(undefined, 'editor', { ...detail, editions: [dvd] })
    await wrapper.get('#edition-format').setValue('Blu-ray')
    await wrapper.get('#regions').trigger('click')
    expect(wrapper.get('[aria-label="Remove Region 2"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Review regions after changing media format')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(catalogApi.updateEdition).toHaveBeenCalledWith(2, 4, expect.objectContaining({ media_format: 'Blu-ray', regions: ['Region 2'], languages: ['German', 'Latin'], publisher: 'Custom distributor' }))
  })
  it('detects a real EAN-13 barcode, hides Source, and sends manual source semantics', async () => {
    const wrapper = await view()
    await button(wrapper, 'Barcodes & IDs')?.trigger('click')
    await button(wrapper, 'Add barcode or ID')?.trigger('click')
    expect(wrapper.text()).not.toContain('Source')
    await wrapper.get('input').setValue('5053083188269')
    expect(wrapper.text()).toContain('Detected type: EAN-13')
    vi.mocked(catalogApi.createIdentifier).mockResolvedValue({ id: 8, edition_id: 4, type: 'EAN-13', value: '5053083188269', source: 'manual' })
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(catalogApi.createIdentifier).toHaveBeenCalledWith(2, 4, { type: 'EAN-13', value: '5053083188269', source: 'manual' })
  })
  it('allows custom types, keeps duplicate form state, and confirms deletion', async () => {
    const wrapper = await view()
    await button(wrapper, 'Barcodes & IDs')?.trigger('click')
    await button(wrapper, 'Add barcode or ID')?.trigger('click')
    await wrapper.get('input').setValue('ABC-12345')
    expect(wrapper.text()).toContain('Choose a type for this custom ID.')
    await wrapper.get('#identifier-type').setValue('__custom__')
    await wrapper.get('#identifier-type-custom').setValue('Internal ID')
    vi.mocked(catalogApi.createIdentifier).mockRejectedValue(new ApiError(409))
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('already exists')
    expect((wrapper.get('input').element as HTMLInputElement).value).toBe('ABC-12345')
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
