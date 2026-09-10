import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/api/client'
import type { Edition, Identifier } from '@/api/catalog'
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
const edition: Edition = { id: 3, catalog_entry_id: 2, display_name: 'Director\'s Cut', release_date: '2024-03-15', publisher: 'Stashive Pictures', region: 'B', language: 'German' }
const identifier: Identifier = { id: 4, edition_id: 3, type: 'EAN', value: '1234567890123', source: 'Manual' }

async function view(
  role: 'owner' | 'admin' | 'editor' | 'viewer' = 'owner',
  editions: Edition[] = [edition],
  identifiers: Record<number, Identifier[]> = { 3: [identifier] },
) {
  vi.mocked(collectionsApi.getCollection).mockResolvedValue({ id: 1, name: 'Films', type: 'movies', description: null, role, owner: { id: 1, username: 'owner', display_name: null } })
  vi.mocked(api.getCatalog).mockResolvedValue(entry)
  vi.mocked(api.listEditions).mockResolvedValue(editions)
  vi.mocked(api.listIdentifiers).mockImplementation(async (_collectionId, editionId) => identifiers[editionId] ?? [])
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

function identifierForm(wrapper: VueWrapper) {
  const form = wrapper.findAll('form').find((candidate) => candidate.text().includes('identifier'))
  if (!form) throw new Error('Identifier form was not found')
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

  it('renders identifiers beneath their matching edition and omits an absent source', async () => {
    const secondEdition: Edition = { ...edition, id: 5, display_name: 'UHD edition' }
    const noSourceIdentifier: Identifier = { id: 6, edition_id: 5, type: 'UPC', value: '012345678905', source: null }
    const wrapper = await view('owner', [edition, secondEdition], { 3: [identifier], 5: [noSourceIdentifier] })

    const editions = wrapper.findAll('li').filter((candidate) => candidate.find('h3').exists())
    expect(editions[0].text()).toContain('EAN: 1234567890123')
    expect(editions[0].text()).toContain('Manual')
    expect(editions[0].text()).not.toContain('012345678905')
    expect(editions[1].text()).toContain('UPC: 012345678905')
    expect(editions[1].text()).not.toContain('Manual')
  })

  it.each(['owner', 'admin', 'editor'] as const)('%s can manage identifiers', async (role) => {
    const wrapper = await view(role)

    expect(button(wrapper, 'Add identifier')).toBeDefined()
    expect(button(wrapper, 'Edit identifier')).toBeDefined()
    expect(button(wrapper, 'Delete identifier')).toBeDefined()
  })

  it('keeps viewers read-only for identifiers', async () => {
    const wrapper = await view('viewer')

    expect(wrapper.text()).toContain('EAN: 1234567890123')
    expect(button(wrapper, 'Add identifier')).toBeUndefined()
    expect(button(wrapper, 'Edit identifier')).toBeUndefined()
    expect(button(wrapper, 'Delete identifier')).toBeUndefined()
  })

  it('creates an identifier with type, value, and source without reloading the page', async () => {
    const created: Identifier = { id: 7, edition_id: 3, type: 'UPC', value: '012345678905', source: 'Imported' }
    vi.mocked(api.createIdentifier).mockResolvedValue(created)
    const wrapper = await view()
    await button(wrapper, 'Add identifier')?.trigger('click')
    await input(wrapper, 'Identifier type').setValue(' UPC ')
    await input(wrapper, 'Identifier value').setValue(' 012345678905 ')
    await input(wrapper, 'Identifier source').setValue(' Imported ')
    await identifierForm(wrapper).trigger('submit')
    await flushPromises()

    expect(api.createIdentifier).toHaveBeenCalledWith(1, 3, { type: 'UPC', value: '012345678905', source: 'Imported' })
    expect(api.getCatalog).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('UPC: 012345678905')
    expect(button(wrapper, 'Create identifier')).toBeUndefined()
  })

  it('creates an identifier with an explicit null source when source is omitted', async () => {
    vi.mocked(api.createIdentifier).mockResolvedValue({ id: 7, edition_id: 3, type: 'UPC', value: '012345678905', source: null })
    const wrapper = await view()
    await button(wrapper, 'Add identifier')?.trigger('click')
    await input(wrapper, 'Identifier type').setValue('UPC')
    await input(wrapper, 'Identifier value').setValue('012345678905')
    await identifierForm(wrapper).trigger('submit')
    await flushPromises()

    expect(api.createIdentifier).toHaveBeenCalledWith(1, 3, { type: 'UPC', value: '012345678905', source: null })
  })

  it.each(['Identifier type', 'Identifier value'] as const)('does not create an identifier with whitespace-only %s', async (label) => {
    const wrapper = await view()
    await button(wrapper, 'Add identifier')?.trigger('click')
    await input(wrapper, 'Identifier type').setValue(label === 'Identifier type' ? '   ' : 'EAN')
    await input(wrapper, 'Identifier value').setValue(label === 'Identifier value' ? '   ' : '1234567890123')
    await identifierForm(wrapper).trigger('submit')

    expect(api.createIdentifier).not.toHaveBeenCalled()
    expect(button(wrapper, 'Create identifier')).toBeDefined()
    expect(wrapper.get('[role="alert"]').text()).toBe('Identifier type and value are required.')
  })

  it('shows a safe duplicate message after a create conflict', async () => {
    vi.mocked(api.createIdentifier).mockRejectedValue(new ApiError(409))
    const wrapper = await view()
    await button(wrapper, 'Add identifier')?.trigger('click')
    await input(wrapper, 'Identifier type').setValue('EAN')
    await input(wrapper, 'Identifier value').setValue('1234567890123')
    await identifierForm(wrapper).trigger('submit')
    await flushPromises()

    expect(button(wrapper, 'Create identifier')).toBeDefined()
    expect(wrapper.get('[role="alert"]').text()).toBe('This identifier already exists for this edition.')
  })

  it.each([
    [403, 'You do not have permission for this action.'],
    [422, 'Check the entered identifier details.'],
    [500, 'This action could not be completed. Please try again.'],
  ])('shows a safe identifier create error for HTTP %i', async (status, expectedMessage) => {
    vi.mocked(api.createIdentifier).mockRejectedValue(new ApiError(status))
    const wrapper = await view()
    await button(wrapper, 'Add identifier')?.trigger('click')
    await input(wrapper, 'Identifier type').setValue('EAN')
    await input(wrapper, 'Identifier value').setValue('1234567890123')
    await identifierForm(wrapper).trigger('submit')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe(expectedMessage)
  })

  it('edits all identifier fields and updates the local identifier list', async () => {
    const updated: Identifier = { ...identifier, type: 'UPC', value: '012345678905', source: 'Verified' }
    vi.mocked(api.updateIdentifier).mockResolvedValue(updated)
    const wrapper = await view()
    await button(wrapper, 'Edit identifier')?.trigger('click')

    expect(input(wrapper, 'Identifier type').element.value).toBe('EAN')
    expect(input(wrapper, 'Identifier value').element.value).toBe('1234567890123')
    expect(input(wrapper, 'Identifier source').element.value).toBe('Manual')
    await input(wrapper, 'Identifier type').setValue('UPC')
    await input(wrapper, 'Identifier value').setValue('012345678905')
    await input(wrapper, 'Identifier source').setValue('Verified')
    await identifierForm(wrapper).trigger('submit')
    await flushPromises()

    expect(api.updateIdentifier).toHaveBeenCalledWith(1, 3, 4, { type: 'UPC', value: '012345678905', source: 'Verified' })
    expect(wrapper.text()).toContain('UPC: 012345678905')
    expect(wrapper.text()).toContain('Verified')
    expect(button(wrapper, 'Save identifier')).toBeUndefined()
  })

  it('sends an explicit null source when an identifier source is cleared', async () => {
    vi.mocked(api.updateIdentifier).mockResolvedValue({ ...identifier, source: null })
    const wrapper = await view()
    await button(wrapper, 'Edit identifier')?.trigger('click')
    await input(wrapper, 'Identifier source').setValue('')
    await identifierForm(wrapper).trigger('submit')
    await flushPromises()

    expect(api.updateIdentifier).toHaveBeenCalledWith(1, 3, 4, { type: 'EAN', value: '1234567890123', source: null })
  })

  it('cancels identifier editing without mutation', async () => {
    const wrapper = await view()
    await button(wrapper, 'Edit identifier')?.trigger('click')
    await input(wrapper, 'Identifier value').setValue('Changed')
    await button(wrapper, 'Cancel')?.trigger('click')

    expect(api.updateIdentifier).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('EAN: 1234567890123')
    expect(button(wrapper, 'Save identifier')).toBeUndefined()
  })

  it.each(['Identifier type', 'Identifier value'] as const)('does not update an identifier with whitespace-only %s', async (label) => {
    const wrapper = await view()
    await button(wrapper, 'Edit identifier')?.trigger('click')
    await input(wrapper, label).setValue('   ')
    await identifierForm(wrapper).trigger('submit')

    expect(api.updateIdentifier).not.toHaveBeenCalled()
    expect(button(wrapper, 'Save identifier')).toBeDefined()
    expect(wrapper.get('[role="alert"]').text()).toBe('Identifier type and value are required.')
  })

  it('keeps identifier and edit input visible after an update duplicate conflict', async () => {
    vi.mocked(api.updateIdentifier).mockRejectedValue(new ApiError(409))
    const wrapper = await view()
    await button(wrapper, 'Edit identifier')?.trigger('click')
    await input(wrapper, 'Identifier value').setValue('Duplicate value')
    await identifierForm(wrapper).trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('EAN: 1234567890123')
    expect(input(wrapper, 'Identifier value').element.value).toBe('Duplicate value')
    expect(wrapper.get('[role="alert"]').text()).toBe('This identifier already exists for this edition.')
  })

  it('requires confirmation before deleting an identifier and supports cancellation', async () => {
    const wrapper = await view()
    await button(wrapper, 'Delete identifier')?.trigger('click')

    expect(api.deleteIdentifier).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Delete this identifier?')
    await button(wrapper, 'Cancel')?.trigger('click')
    expect(api.deleteIdentifier).not.toHaveBeenCalled()
    expect(button(wrapper, 'Confirm delete identifier')).toBeUndefined()
  })

  it('deletes the confirmed identifier once without closing its edition or catalog entry', async () => {
    vi.mocked(api.deleteIdentifier).mockResolvedValue()
    const wrapper = await view()
    await button(wrapper, 'Delete identifier')?.trigger('click')
    await button(wrapper, 'Confirm delete identifier')?.trigger('click')
    await flushPromises()

    expect(api.deleteIdentifier).toHaveBeenCalledTimes(1)
    expect(api.deleteIdentifier).toHaveBeenCalledWith(1, 3, 4)
    expect(wrapper.text()).not.toContain('EAN: 1234567890123')
    expect(wrapper.text()).toContain("Director's Cut")
    expect(wrapper.text()).toContain('Alien')
  })

  it('keeps an identifier visible and reports a safe error when deletion fails', async () => {
    vi.mocked(api.deleteIdentifier).mockRejectedValue(new ApiError(404))
    const wrapper = await view()
    await button(wrapper, 'Delete identifier')?.trigger('click')
    await button(wrapper, 'Confirm delete identifier')?.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('EAN: 1234567890123')
    expect(button(wrapper, 'Confirm delete identifier')).toBeDefined()
    expect(wrapper.get('[role="alert"]').text()).toBe('This identifier is no longer available.')
  })
})
