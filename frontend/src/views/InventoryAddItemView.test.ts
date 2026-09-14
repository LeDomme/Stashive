import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as collectionsApi from '@/api/collections'
import * as libraryApi from '@/api/library'
import * as locationsApi from '@/api/locations'
import { EDITION_PRESETS } from '@/constants/inventoryPresets'
import InventoryAddItemView from './InventoryAddItemView.vue'

vi.mock('@/api/collections'); vi.mock('@/api/library'); vi.mock('@/api/locations')
const router = createRouter({ history: createMemoryHistory(), routes: [
  { path: '/collections/:collectionId/inventory/add', name: 'inventory-add', component: InventoryAddItemView },
  { path: '/collections/:collectionId/inventory', name: 'inventory', component: InventoryAddItemView },
  { path: '/collections/:collectionId/inventory/:catalogEntryId', name: 'inventory-title', component: InventoryAddItemView },
] })
const title = { id: 2, collection_id: 1, display_title: 'Alien', type: 'movies', sort_title: null, notes: null }
const editions = [
  { id: 3, catalog_entry_id: 2, display_name: 'Special Edition', media_format: 'Blu-ray', release_date: null, publisher: null, regions: [], languages: [], identifiers: [], copies: [{ id: 8 }] },
  { id: 4, catalog_entry_id: 2, display_name: 'Standard Edition', media_format: 'LaserDisc', release_date: null, publisher: null, regions: [], languages: [], identifiers: [], copies: [{ id: 9 }, { id: 10 }] },
]
const detail = { catalog_entry: title, editions }
async function view(role: 'owner' | 'editor' | 'viewer' = 'editor', collectionType = 'movies') {
  vi.mocked(collectionsApi.getCollection).mockResolvedValue({ ...title, name: 'Films', type: collectionType, role, owner: { id: 1, username: 'owner', display_name: null } })
  vi.mocked(locationsApi.listLocationTree).mockResolvedValue([])
  vi.mocked(libraryApi.searchTitles).mockResolvedValue([{ id: 2, catalog_entry_id: 2, display_title: 'Alien', sort_title: null, type: 'movies', edition_count: 2, copy_count: 3, media_formats: ['Blu-ray'] }])
  vi.mocked(libraryApi.getLibraryTitle).mockResolvedValue(detail)
  await router.push('/collections/1/inventory/add')
  const wrapper = mount(InventoryAddItemView, { global: { plugins: [createPinia(), router] } })
  await flushPromises()
  return wrapper
}
const button = (wrapper: ReturnType<typeof mount>, label: string) => wrapper.findAll('button').find((candidate) => candidate.text() === label)!
async function createTitle(wrapper: ReturnType<typeof mount>, name = 'Arrival') {
  await wrapper.get('input').setValue(name)
  await button(wrapper, `Create new title "${name}"`).trigger('click')
  await flushPromises()
}
async function useExistingTitle(wrapper: ReturnType<typeof mount>) {
  await wrapper.get('input').setValue('Alien')
  await new Promise((resolve) => setTimeout(resolve, 350)); await flushPromises()
  await button(wrapper, 'Use existing').trigger('click'); await flushPromises()
}
async function openMulti(wrapper: ReturnType<typeof mount>, id: string) { await wrapper.get(`#${id}`).trigger('click') }
afterEach(() => vi.clearAllMocks())

describe('InventoryAddItemView', () => {
  it('keeps viewers read-only and starts progressively', async () => {
    const viewer = await view('viewer'); expect(viewer.text()).toContain('do not have permission'); expect(viewer.find('form').exists()).toBe(false)
    const editor = await view(); expect(editor.text()).toContain('Title'); expect(editor.text()).not.toContain('Physical copy')
  })

  it('uses one edition dropdown with readable singular/plural labels and a create option', async () => {
    const wrapper = await view(); await useExistingTitle(wrapper)
    const select = wrapper.get('select').element as HTMLSelectElement
    expect([...select.options].map((option) => option.text)).toEqual(['Select an edition...', 'Special Edition · Blu-ray · 1 copy', 'Standard Edition · LaserDisc · 2 copies', 'Create new edition'])
    expect(wrapper.text()).not.toContain('Use this edition')
    expect(wrapper.text()).not.toContain('Special EditionBlu-ray')
  })

  it('shows only physical copy controls for an existing edition and resets stale new-edition state when switching', async () => {
    const wrapper = await view(); await useExistingTitle(wrapper)
    await wrapper.get('select').setValue('3')
    expect(wrapper.text()).toContain('Physical copy'); expect(wrapper.find('#edition').exists()).toBe(false)
    await wrapper.get('select').setValue('__new__')
    expect(wrapper.find('#edition').exists()).toBe(true); expect(wrapper.text()).toContain('Movie metadata')
    await wrapper.get('#edition').setValue('__custom__'); await wrapper.get('#edition-custom').setValue('40th Anniversary Edition')
    await wrapper.get('select').setValue('4')
    expect(wrapper.find('#edition').exists()).toBe(false); expect(wrapper.find('#edition-custom').exists()).toBe(false)
    expect(wrapper.text()).toContain('Physical copy')
  })

  it('submits a new title, new edition, multi values and an unassigned copy', async () => {
    vi.mocked(libraryApi.addItem).mockResolvedValue({ catalog_entry_id: 12, edition_id: 13, inventory_item_id: 14 })
    const wrapper = await view(); await createTitle(wrapper)
    await wrapper.get('select').setValue('__new__')
    await wrapper.get('#edition').setValue('Steelbook'); await wrapper.get('#media-format').setValue('Blu-ray')
    await openMulti(wrapper, 'regions'); await wrapper.get('#regions-popover input[type="checkbox"]').setValue(true)
    await openMulti(wrapper, 'languages'); await wrapper.get('#languages-popover input[type="checkbox"]').setValue(true)
    await wrapper.get('#condition').setValue('Sealed'); await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(libraryApi.addItem).toHaveBeenCalledWith(1, expect.objectContaining({
      title: { existing_id: null, new: { display_title: 'Arrival', sort_title: null, notes: null, type: 'movies' } },
      edition: { existing_id: null, new: expect.objectContaining({ display_name: 'Steelbook', media_format: 'Blu-ray', regions: ['Region A'], languages: ['German'] }) },
      copy: { condition: 'Sealed', notes: null, location_id: null },
    }))
  })

  it('submits a new edition and copy for an existing title without changing the payload contract', async () => {
    vi.mocked(libraryApi.addItem).mockResolvedValue({ catalog_entry_id: 2, edition_id: 13, inventory_item_id: 14 })
    const wrapper = await view(); await useExistingTitle(wrapper); await wrapper.get('select').setValue('__new__')
    await wrapper.get('#edition').setValue('__custom__'); await wrapper.get('#edition-custom').setValue('40th Anniversary Edition')
    await wrapper.get('#media-format').setValue('__custom__'); await wrapper.get('#media-format-custom').setValue('Video CD')
    await wrapper.get('#condition').setValue('__custom__'); await wrapper.get('#condition-custom').setValue('Like new')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(libraryApi.addItem).toHaveBeenCalledWith(1, expect.objectContaining({ title: { existing_id: 2, new: null }, edition: expect.objectContaining({ existing_id: null, new: expect.objectContaining({ display_name: '40th Anniversary Edition', media_format: 'Video CD' }) }), copy: { condition: 'Like new', notes: null, location_id: null } }))
  })

  it('submits only the selected existing edition and copy details', async () => {
    vi.mocked(libraryApi.addItem).mockResolvedValue({ catalog_entry_id: 2, edition_id: 3, inventory_item_id: 14 })
    const wrapper = await view(); await useExistingTitle(wrapper); await wrapper.get('select').setValue('3')
    await wrapper.get('#condition').setValue('Good'); await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(libraryApi.addItem).toHaveBeenCalledWith(1, expect.objectContaining({ title: { existing_id: 2, new: null }, edition: { existing_id: 3, new: null }, copy: { condition: 'Good', notes: null, location_id: null } }))
  })

  it('retains state after errors, resets dependent state on a title change, and omits movie controls for board games', async () => {
    vi.mocked(libraryApi.addItem).mockRejectedValue(new Error('offline'))
    const wrapper = await view(); await createTitle(wrapper); await wrapper.get('select').setValue('__new__')
    await wrapper.get('#edition').setValue('__custom__'); await wrapper.get('#edition-custom').setValue('40th Anniversary Edition')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('could not be added'); expect(wrapper.find('#edition-custom').exists()).toBe(true)
    await button(wrapper, 'Change title').trigger('click'); expect(wrapper.find('#edition').exists()).toBe(false)
    const boardGames = await view('editor', 'board_games'); await createTitle(boardGames); await boardGames.get('select').setValue('__new__')
    expect(boardGames.text()).not.toContain('Movie metadata')
  })

  it('keeps Box Set as an existing custom value while offering Special Edition and no Box Set preset', () => {
    expect(EDITION_PRESETS).toContain('Special Edition'); expect(EDITION_PRESETS).not.toContain('Box Set')
  })
})
