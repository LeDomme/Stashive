import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/api/client'
import * as api from '@/api/catalog'
import * as collectionsApi from '@/api/collections'
import CatalogDetailView from './CatalogDetailView.vue'

vi.mock('@/api/catalog')
vi.mock('@/api/collections')

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/collections/:collectionId/catalog', name: 'catalog', component: CatalogDetailView },
    { path: '/collections/:collectionId/catalog/:entryId', name: 'catalog-detail', component: CatalogDetailView },
  ],
})
const entry = { id: 2, collection_id: 1, display_title: 'Alien', type: 'movie', sort_title: 'Alien, The', notes: 'Classic' }
const edition = { id: 3, catalog_entry_id: 2, display_name: 'Director\'s Cut', release_date: '2024-03-15', publisher: 'Stashive Pictures', region: 'B', language: 'German' }

async function view(role: 'owner' | 'admin' | 'editor' | 'viewer' = 'owner', editions = [edition]) {
  vi.mocked(collectionsApi.getCollection).mockResolvedValue({ id: 1, name: 'Films', type: 'movies', description: null, role, owner: { id: 1, username: 'owner', display_name: null } })
  vi.mocked(api.getCatalog).mockResolvedValue(entry)
  vi.mocked(api.listEditions).mockResolvedValue(editions)
  await router.push('/collections/1/catalog/2')
  const wrapper = mount(CatalogDetailView, { global: { plugins: [createPinia(), router] } })
  await flushPromises()
  return wrapper
}

function button(wrapper: VueWrapper, name: string) {
  return wrapper.findAll('button').find((candidate) => candidate.text() === name)
}

function input(wrapper: VueWrapper, label: string) {
  const field = wrapper.findAll('label').find((candidate) => candidate.text().startsWith(label))
  if (!field) throw new Error(`Input with label ${label} was not found`)
  return field.get('input')
}

function editionForm(wrapper: VueWrapper) {
  const form = wrapper.findAll('form').find((candidate) => candidate.text().includes('Save edition'))
  if (!form) throw new Error('Edition form was not found')
  return form
}

afterEach(() => vi.clearAllMocks())

describe('CatalogDetailView', () => {
  it('renders optional catalog detail fields', async () => {
    const wrapper = await view()

    expect(wrapper.text()).toContain('Alien, The')
    expect(wrapper.text()).toContain('Classic')
  })

  it.each(['owner', 'admin', 'editor'] as const)('%s can edit and delete catalog entries', async (role) => {
    const wrapper = await view(role)

    expect(button(wrapper, 'Edit entry')).toBeDefined()
    expect(button(wrapper, 'Delete entry')).toBeDefined()
  })

  it('keeps viewers read-only for catalog entries', async () => {
    const wrapper = await view('viewer')

    expect(button(wrapper, 'Edit entry')).toBeUndefined()
    expect(button(wrapper, 'Delete entry')).toBeUndefined()
  })

  it('sends explicit nulls for catalog fields and requires entry delete confirmation', async () => {
    vi.mocked(api.updateCatalog).mockResolvedValue({ ...entry, sort_title: null, notes: null })
    const wrapper = await view()
    await button(wrapper, 'Edit entry')?.trigger('click')
    await input(wrapper, 'Sort title').setValue('')
    const notes = wrapper.find('textarea')
    await notes.setValue('')
    await wrapper.findAll('form').find((candidate) => candidate.text().includes('Save'))?.trigger('submit')
    await flushPromises()

    expect(api.updateCatalog).toHaveBeenCalledWith(1, 2, expect.objectContaining({ sort_title: null, notes: null }))
    expect(api.deleteCatalog).not.toHaveBeenCalled()
    await button(wrapper, 'Delete entry')?.trigger('click')
    expect(wrapper.text()).toContain('physical inventory copies')
  })

  it('renders all edition metadata', async () => {
    const wrapper = await view()

    expect(wrapper.text()).toContain("Director's Cut")
    expect(wrapper.text()).toContain('2024-03-15')
    expect(wrapper.text()).toContain('Stashive Pictures')
    expect(wrapper.text()).toContain('B')
    expect(wrapper.text()).toContain('German')
  })

  it.each(['owner', 'admin', 'editor'] as const)('%s can edit and delete editions', async (role) => {
    const wrapper = await view(role)

    expect(button(wrapper, 'Edit edition')).toBeDefined()
    expect(button(wrapper, 'Delete edition')).toBeDefined()
  })

  it('keeps viewers read-only for editions', async () => {
    const wrapper = await view('viewer')

    expect(button(wrapper, 'Edit edition')).toBeUndefined()
    expect(button(wrapper, 'Delete edition')).toBeUndefined()
    expect(button(wrapper, 'Add edition')).toBeUndefined()
  })

  it('opens the edition form with the existing values and cancels without mutation', async () => {
    const wrapper = await view()
    await button(wrapper, 'Edit edition')?.trigger('click')

    expect(input(wrapper, 'Display name').element.value).toBe("Director's Cut")
    expect(input(wrapper, 'Release date').element.value).toBe('2024-03-15')
    expect(input(wrapper, 'Publisher').element.value).toBe('Stashive Pictures')
    expect(input(wrapper, 'Region').element.value).toBe('B')
    expect(input(wrapper, 'Language').element.value).toBe('German')

    await input(wrapper, 'Publisher').setValue('Changed publisher')
    await button(wrapper, 'Cancel')?.trigger('click')

    expect(api.updateEdition).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Stashive Pictures')
    expect(button(wrapper, 'Save edition')).toBeUndefined()
  })

  it('saves edited edition fields and refreshes the catalog detail', async () => {
    vi.mocked(api.updateEdition).mockResolvedValue({ ...edition, display_name: 'Theatrical Cut', publisher: 'New publisher' })
    const wrapper = await view()
    vi.mocked(api.listEditions).mockResolvedValueOnce([{ ...edition, display_name: 'Theatrical Cut', publisher: 'New publisher' }])
    await button(wrapper, 'Edit edition')?.trigger('click')
    await input(wrapper, 'Display name').setValue('  Theatrical Cut  ')
    await input(wrapper, 'Publisher').setValue('New publisher')
    await editionForm(wrapper).trigger('submit')
    await flushPromises()

    expect(api.updateEdition).toHaveBeenCalledWith(1, 3, expect.objectContaining({ display_name: 'Theatrical Cut', publisher: 'New publisher' }))
    expect(api.getCatalog).toHaveBeenCalledTimes(2)
    expect(api.listEditions).toHaveBeenCalledTimes(2)
    expect(button(wrapper, 'Save edition')).toBeUndefined()
    expect(wrapper.text()).toContain('Theatrical Cut')
  })

  it('validates an empty edition display name without updating', async () => {
    const wrapper = await view()
    await button(wrapper, 'Edit edition')?.trigger('click')
    await input(wrapper, 'Display name').setValue('   ')
    await editionForm(wrapper).trigger('submit')

    expect(wrapper.get('[role="alert"]').text()).toBe('Edition name is required.')
    expect(api.updateEdition).not.toHaveBeenCalled()
  })

  it('sends explicit nulls when optional edition fields are cleared', async () => {
    vi.mocked(api.updateEdition).mockResolvedValue({ ...edition, release_date: null, publisher: null, region: null, language: null })
    const wrapper = await view()
    await button(wrapper, 'Edit edition')?.trigger('click')
    await input(wrapper, 'Release date').setValue('')
    await input(wrapper, 'Publisher').setValue('')
    await input(wrapper, 'Region').setValue('')
    await input(wrapper, 'Language').setValue('')
    await editionForm(wrapper).trigger('submit')
    await flushPromises()

    expect(api.updateEdition).toHaveBeenCalledWith(1, 3, {
      display_name: "Director's Cut",
      release_date: null,
      publisher: null,
      region: null,
      language: null,
    })
  })

  it('keeps the edition visible and editable after an update error', async () => {
    vi.mocked(api.updateEdition).mockRejectedValue(new ApiError(403))
    const wrapper = await view()
    await button(wrapper, 'Edit edition')?.trigger('click')
    await input(wrapper, 'Publisher').setValue('Changed publisher')
    await editionForm(wrapper).trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain("Director's Cut")
    expect(button(wrapper, 'Save edition')).toBeDefined()
    expect(input(wrapper, 'Publisher').element.value).toBe('Changed publisher')
    expect(wrapper.get('[role="alert"]').text()).toBe('You do not have permission for this action.')
  })

  it('requires confirmation and explains the edition delete cascade', async () => {
    const wrapper = await view()
    await button(wrapper, 'Delete edition')?.trigger('click')

    expect(api.deleteEdition).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('removes its identifiers and all physical inventory copies')
    expect(wrapper.text()).toContain('The catalog entry remains.')
  })

  it('cancels an edition delete without calling the API', async () => {
    const wrapper = await view()
    await button(wrapper, 'Delete edition')?.trigger('click')
    await button(wrapper, 'Cancel')?.trigger('click')

    expect(api.deleteEdition).not.toHaveBeenCalled()
    expect(button(wrapper, 'Confirm delete')).toBeUndefined()
  })

  it('disables the confirmation while deletion is in progress', async () => {
    let resolveDelete: (() => void) | undefined
    vi.mocked(api.deleteEdition).mockImplementation(() => new Promise<void>((resolve) => { resolveDelete = resolve }))
    const wrapper = await view()
    await button(wrapper, 'Delete edition')?.trigger('click')
    await button(wrapper, 'Confirm delete')?.trigger('click')

    const confirm = button(wrapper, 'Deleting…')
    expect(api.deleteEdition).toHaveBeenCalledTimes(1)
    expect(confirm?.attributes('disabled')).toBeDefined()

    resolveDelete?.()
    await flushPromises()
  })

  it('deletes once on confirmation and refreshes the catalog detail', async () => {
    vi.mocked(api.deleteEdition).mockResolvedValue()
    const wrapper = await view()
    vi.mocked(api.listEditions).mockResolvedValueOnce([])
    await button(wrapper, 'Delete edition')?.trigger('click')
    await button(wrapper, 'Confirm delete')?.trigger('click')
    await flushPromises()

    expect(api.deleteEdition).toHaveBeenCalledTimes(1)
    expect(api.deleteEdition).toHaveBeenCalledWith(1, 3)
    expect(api.getCatalog).toHaveBeenCalledTimes(2)
    expect(api.listEditions).toHaveBeenCalledTimes(2)
    expect(button(wrapper, 'Confirm delete')).toBeUndefined()
    expect(wrapper.text()).not.toContain("Director's Cut")
  })

  it('keeps the edition visible after a delete error', async () => {
    vi.mocked(api.deleteEdition).mockRejectedValue(new ApiError(409))
    const wrapper = await view()
    await button(wrapper, 'Delete edition')?.trigger('click')
    await button(wrapper, 'Confirm delete')?.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain("Director's Cut")
    expect(button(wrapper, 'Confirm delete')).toBeDefined()
    expect(wrapper.get('[role="alert"]').text()).toBe('This change conflicts with existing data.')
  })
})
