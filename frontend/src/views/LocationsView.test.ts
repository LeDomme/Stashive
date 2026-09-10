import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/client'
import * as collectionApi from '@/api/collections'
import * as locationApi from '@/api/locations'
import LocationsView from './LocationsView.vue'

vi.mock('@/api/collections', () => ({ getCollection: vi.fn() }))
vi.mock('@/api/locations', () => ({ listLocationTree: vi.fn(), createLocation: vi.fn(), updateLocation: vi.fn(), deleteLocation: vi.fn() }))

const router = createRouter({ history: createMemoryHistory(), routes: [
  { path: '/collections/:collectionId', name: 'collection-detail', component: LocationsView },
  { path: '/collections/:collectionId/locations', name: 'locations', component: LocationsView },
  { path: '/collections/:collectionId/inventory', name: 'inventory', component: LocationsView },
  { path: '/collections/:collectionId/catalog', name: 'catalog', component: LocationsView },
  { path: '/collections/:collectionId/settings', name: 'collection-settings', component: LocationsView },
] })

const node = (id: number, name: string, children: locationApi.LocationTreeNode[] = []): locationApi.LocationTreeNode => ({ id, collection_id: 1, parent_id: null, name, type: 'shelf', description: name === 'Shelf' ? 'Blu-rays' : null, children })
const tree = [node(1, 'House', [node(2, 'Basement', [node(3, 'Shelf')])]), node(4, 'Garage')]

async function mountView(
  role: 'owner' | 'admin' | 'editor' | 'viewer' = 'owner',
  locationTree: locationApi.LocationTreeNode[] = tree,
) {
  vi.mocked(collectionApi.getCollection).mockResolvedValue({ id: 1, name: 'Films', type: 'movies', description: null, role, owner: { id: 1, username: 'owner', display_name: null } })
  vi.mocked(locationApi.listLocationTree).mockResolvedValue(locationTree)
  await router.push('/collections/1/locations')
  const wrapper = mount(LocationsView, { global: { plugins: [createPinia(), router] } })
  await flushPromises()
  return wrapper
}

afterEach(() => vi.clearAllMocks())

describe('LocationsView', () => {
  it('renders a nested tree in backend order with types and descriptions', async () => {
    const wrapper = await mountView()
    expect(wrapper.get('[aria-label="Location tree"]').text()).toContain('House')
    expect(wrapper.text()).toContain('Basement')
    expect(wrapper.text()).toContain('Shelf')
    expect(wrapper.text()).toContain('Blu-rays')
    expect(wrapper.text().indexOf('House')).toBeLessThan(wrapper.text().indexOf('Garage'))
    expect(wrapper.findAll('.location-type-badge').map((badge) => badge.text())).toEqual(['Shelf', 'Shelf', 'Shelf', 'Shelf'])
  })

  it('keeps the type badge separate and updates the selected location detail', async () => {
    const wrapper = await mountView()
    const shelf = wrapper.findAll('.location-node__content')[2]
    await shelf.trigger('click')

    expect(shelf.find('.location-node__name').text()).toBe('Shelf')
    expect(shelf.find('.location-type-badge').text()).toBe('Shelf')
    expect(shelf.classes()).toContain('is-selected')
    expect(wrapper.get('[aria-labelledby="selected-location-heading"]').text()).toContain('Blu-rays')
  })

  it('shows the editable empty state and a read-only viewer state', async () => {
    const owner = await mountView('owner', [])
    expect(owner.get('button').text()).toContain('Add root location')
    const viewer = await mountView('viewer', [])
    expect(viewer.text()).toContain('No locations have been created')
    expect(viewer.find('button').exists()).toBe(false)
  })

  it('shows a safe unavailable state for a directly opened inaccessible collection', async () => {
    vi.mocked(collectionApi.getCollection).mockRejectedValue(new ApiError(404))
    await router.push('/collections/1/locations')
    const wrapper = mount(LocationsView, { global: { plugins: [createPinia(), router] } })
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('no longer available')
  })

  it.each(['owner', 'admin', 'editor'] as const)('shows mutation controls for %s', async (role) => {
    const wrapper = await mountView(role)
    expect(wrapper.findAll('button').map((button) => button.text())).toContain('Add child')
    expect(wrapper.findAll('button').map((button) => button.text())).toContain('Edit location')
  })

  it('creates a root and a selected child with typed payloads', async () => {
    vi.mocked(locationApi.createLocation).mockResolvedValue(tree[0])
    const wrapper = await mountView()
    await wrapper.get('button').trigger('click')
    const forms = wrapper.findAll('form')
    await forms[0].get('input').setValue(' Root ')
    await forms[0].trigger('submit.prevent')
    await flushPromises()
    expect(locationApi.createLocation).toHaveBeenCalledWith(1, { name: 'Root', type: 'room', description: null, parent_id: null })
    await wrapper.findAll('button').find((button) => button.text() === 'Add child')!.trigger('click')
    const childForm = wrapper.find('form')
    await childForm.get('input').setValue('Child')
    await childForm.trigger('submit.prevent')
    await flushPromises()
    expect(locationApi.createLocation).toHaveBeenLastCalledWith(1, { name: 'Child', type: 'room', description: null, parent_id: 1 })
  })

  it('edits metadata, can make a child root, and excludes self and descendants from parents', async () => {
    vi.mocked(locationApi.updateLocation).mockResolvedValue(tree[0])
    const wrapper = await mountView()
    await wrapper.findAll('button').find((button) => button.text() === 'Edit location')!.trigger('click')
    const form = wrapper.find('form')
    await form.get('input').setValue('House renamed')
    const parentSelect = form.findAll('select')[1]
    expect(parentSelect.text()).toContain('No parent / Root')
    expect(parentSelect.text()).not.toContain('House')
    expect(parentSelect.text()).not.toContain('Basement')
    await parentSelect.setValue('')
    await form.trigger('submit.prevent')
    await flushPromises()
    expect(locationApi.updateLocation).toHaveBeenCalledWith(1, 1, { name: 'House renamed', type: 'shelf', description: null, parent_id: null })
  })

  it('requires delete confirmation and shows safe conflict errors', async () => {
    vi.mocked(locationApi.deleteLocation).mockRejectedValue(new ApiError(409))
    const wrapper = await mountView()
    await wrapper.findAll('.location-node__content')[2].trigger('click')
    await wrapper.find('[aria-label="Delete Shelf"]').trigger('click')
    expect(locationApi.deleteLocation).not.toHaveBeenCalled()
    await wrapper.findAll('button').find((button) => button.text() === 'Confirm delete')!.trigger('click')
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('still contains child locations')
  })
})
