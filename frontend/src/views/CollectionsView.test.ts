import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import * as collectionApi from '@/api/collections'
import CollectionsView from './CollectionsView.vue'

vi.mock('@/api/collections', () => ({
  listCollections: vi.fn(),
  createCollection: vi.fn(),
  getCollection: vi.fn(),
  updateCollection: vi.fn(),
  deleteCollection: vi.fn(),
}))

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/collections', name: 'collections', component: CollectionsView },
    { path: '/collections/:collectionId', name: 'collection-detail', component: CollectionsView },
  ],
})

function mountView() {
  return mount(CollectionsView, { global: { plugins: [createPinia(), router] } })
}

beforeEach(async () => {
  vi.mocked(collectionApi.listCollections).mockResolvedValue([])
  await router.push('/collections')
})

afterEach(() => {
  vi.clearAllMocks()
})

describe('CollectionsView', () => {
  it('renders collections returned by the API', async () => {
    vi.mocked(collectionApi.listCollections).mockResolvedValue([
      { id: 1, name: 'Films', type: 'movies', description: 'Blu-rays', role: 'owner' },
      { id: 2, name: 'Shared games', type: 'board_games', description: null, role: 'viewer' },
    ])

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.get('[aria-label="Collections"]').text()).toContain('Films')
    expect(wrapper.text()).toContain('Blu-rays')
    expect(wrapper.text()).toContain('owner')
    expect(wrapper.text()).toContain('Shared games')
    expect(wrapper.text()).toContain('No description yet.')
  })

  it('renders an empty state when the API returns no collections', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('No collections yet')
  })

  it('creates a collection and navigates to its detail page', async () => {
    vi.mocked(collectionApi.createCollection).mockResolvedValue({ id: 42, name: 'Films', role: 'owner' })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.get('input').setValue(' Films ')
    await wrapper.get('textarea').setValue('  Blu-rays  ')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(collectionApi.createCollection).toHaveBeenCalledWith({
      name: 'Films',
      type: 'movies',
      description: 'Blu-rays',
    })
    expect(router.currentRoute.value.params.collectionId).toBe('42')
  })

  it('shows a safe error when loading collections fails', async () => {
    vi.mocked(collectionApi.listCollections).mockRejectedValue(new Error('network details'))
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain('Collections could not be loaded')
    expect(wrapper.text()).not.toContain('network details')
  })
})
