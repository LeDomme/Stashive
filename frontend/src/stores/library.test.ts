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
    expect(api.listLibrary).toHaveBeenCalledWith(2); expect(store.titles[0].media_formats).toEqual(['Blu-ray']); expect(store.title?.editions[0].identifiers[0].value).toBe('123')
  })
})
