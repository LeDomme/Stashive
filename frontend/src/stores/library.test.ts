import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '@/api/library'
import { useLibraryStore } from './library'

vi.mock('@/api/library')
beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks() })
describe('library store', () => {
  it('loads summaries and replaces title detail', async () => {
    vi.mocked(api.listLibrary).mockResolvedValue([{ id: 1, catalog_entry_id: 1, display_title: 'Alien', sort_title: null, type: 'movie', edition_count: 1, copy_count: 1, media_formats: ['Blu-ray'] }])
    vi.mocked(api.getLibraryTitle).mockResolvedValue({ catalog_entry: { id: 1, collection_id: 2, display_title: 'Alien', type: 'movie', sort_title: null, notes: null }, editions: [{ id: 3, catalog_entry_id: 1, display_name: 'Special Edition', media_format: 'Blu-ray', release_date: null, publisher: null, region: null, language: null, identifiers: [{ id: 4, edition_id: 3, type: 'EAN', value: '123', source: null }], copies: [] }] })
    const store = useLibraryStore(); await store.load(2); await store.loadDetail(2, 1)
    expect(api.listLibrary).toHaveBeenCalledWith(2, {}); expect(store.titles[0].media_formats).toEqual(['Blu-ray']); expect(store.title?.editions[0].identifiers[0].value).toBe('123')
  })
  it('clears a prior detail before loading another title', async () => {
    let resolveDetail: ((value: Awaited<ReturnType<typeof api.getLibraryTitle>>) => void) | undefined
    vi.mocked(api.getLibraryTitle).mockReturnValue(new Promise((resolve) => { resolveDetail = resolve }))
    const store = useLibraryStore()
    store.title = { catalog_entry: { id: 1, collection_id: 2, display_title: 'Alien', type: 'movie', sort_title: null, notes: null }, editions: [] }
    const loading = store.loadDetail(2, 3)
    expect(store.title).toBeNull()
    resolveDetail?.({ catalog_entry: { id: 3, collection_id: 2, display_title: 'Heat', type: 'movie', sort_title: null, notes: null }, editions: [] })
    await loading
    expect(store.title?.catalog_entry.display_title).toBe('Heat')
  })
  it('searches titles and forwards typed add-item payloads', async () => {
    vi.mocked(api.searchTitles).mockResolvedValue([{ id: 1, catalog_entry_id: 1, display_title: 'Alien', sort_title: null, type: 'movie', edition_count: 1, copy_count: 1, media_formats: [] }])
    vi.mocked(api.addItem).mockResolvedValue({ catalog_entry_id: 1, edition_id: 2, inventory_item_id: 3 })
    const store = useLibraryStore(); await store.searchTitles(2, 'ali')
    const payload = { title: { existing_id: 1, new: null }, edition: { existing_id: 2, new: null }, copy: { condition: null, notes: null, location_id: null } }
    await store.addItem(2, payload)
    expect(store.searchResults[0].display_title).toBe('Alien'); expect(api.addItem).toHaveBeenCalledWith(2, payload)
  })
})
