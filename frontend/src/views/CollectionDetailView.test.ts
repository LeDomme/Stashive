import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/client'
import * as collectionApi from '@/api/collections'
import CollectionDetailView from './CollectionDetailView.vue'

vi.mock('@/api/collections', () => ({
  listCollections: vi.fn(),
  createCollection: vi.fn(),
  getCollection: vi.fn(),
  updateCollection: vi.fn(),
  deleteCollection: vi.fn(),
  listMembers: vi.fn(),
  addMember: vi.fn(),
  updateMember: vi.fn(),
  deleteMember: vi.fn(),
  transferOwnership: vi.fn(),
}))

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/collections', name: 'collections', component: CollectionDetailView },
    { path: '/collections/:collectionId', name: 'collection-detail', component: CollectionDetailView },
  ],
})

function collection(role: 'owner' | 'admin' | 'editor' | 'viewer') {
  return {
    id: 1,
    name: 'Films',
    type: 'movies',
    description: 'Blu-rays',
    role,
    owner: { id: 1, username: 'owner', display_name: 'Collection Owner' },
  }
}

async function mountView(role: 'owner' | 'admin' | 'editor' | 'viewer' = 'owner') {
  vi.mocked(collectionApi.getCollection).mockResolvedValue(collection(role))
  await router.push('/collections/1')
  const wrapper = mount(CollectionDetailView, { global: { plugins: [createPinia(), router] } })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.mocked(collectionApi.deleteCollection).mockResolvedValue()
  vi.mocked(collectionApi.listMembers).mockResolvedValue([
    { id: 2, username: 'member', display_name: 'Member Name', role: 'viewer' },
  ])
})

afterEach(() => {
  vi.clearAllMocks()
})

describe('CollectionDetailView', () => {
  it('renders collection details and the effective role', async () => {
    const wrapper = await mountView('owner')

    expect(wrapper.get('h1').text()).toBe('Films')
    expect(wrapper.text()).toContain('Blu-rays')
    expect(wrapper.text()).toContain('Your role')
    expect(wrapper.text()).toContain('owner')
  })

  it('shows the owner separately from safe member identity data', async () => {
    const wrapper = await mountView('owner')

    expect(wrapper.text()).toContain('Owner: Collection Owner (owner)')
    expect(wrapper.get('[aria-label="Collection members"]').text()).toContain('Member Name (member)')
    expect(wrapper.get('[aria-label="Collection members"]').text()).not.toContain('Collection Owner')
  })

  it.each([
    ['owner', true, true],
    ['admin', true, false],
    ['editor', false, false],
    ['viewer', false, false],
  ] as const)('shows actions for %s according to collection role', async (role, edit, remove) => {
    const wrapper = await mountView(role)

    expect(wrapper.find('button.button-secondary').exists()).toBe(edit)
    expect(wrapper.text().includes('Delete collection')).toBe(remove)
  })

  it('saves edited collection metadata for an owner', async () => {
    vi.mocked(collectionApi.updateCollection).mockResolvedValue({
      id: 1,
      name: 'Renamed films',
      role: 'owner',
    })
    const wrapper = await mountView('owner')

    await wrapper.get('button.button-secondary').trigger('click')
    const editForm = wrapper.findAll('form').find((form) => form.text().includes('Edit collection details'))!
    await editForm.get('input').setValue(' Renamed films ')
    await editForm.trigger('submit.prevent')
    await flushPromises()

    expect(collectionApi.updateCollection).toHaveBeenCalledWith(1, {
      name: 'Renamed films',
      type: 'movies',
      description: 'Blu-rays',
    })
    expect(wrapper.text()).toContain('Renamed films')
  })

  it('requires an explicit confirmation before deleting a collection', async () => {
    const wrapper = await mountView('owner')

    expect(collectionApi.deleteCollection).not.toHaveBeenCalled()
    await wrapper.get('button.button-danger').trigger('click')
    expect(wrapper.text()).toContain('Delete Films?')
    expect(collectionApi.deleteCollection).not.toHaveBeenCalled()
    await wrapper.findAll('button').find((button) => button.text() === 'Confirm delete')!.trigger('click')
    await flushPromises()

    expect(collectionApi.deleteCollection).toHaveBeenCalledWith(1)
    expect(router.currentRoute.value.name).toBe('collections')
  })

  it('adds a member and refreshes the displayed member list', async () => {
    vi.mocked(collectionApi.addMember).mockResolvedValue()
    const wrapper = await mountView('owner')
    vi.mocked(collectionApi.listMembers).mockResolvedValue([
      { id: 3, username: 'new-user', display_name: 'New User', role: 'editor' },
    ])
    const memberForm = wrapper.findAll('form').find((form) => form.text().includes('Add a member'))!

    await memberForm.get('input').setValue(' new-user ')
    await memberForm.get('select').setValue('editor')
    await memberForm.trigger('submit.prevent')
    await flushPromises()

    expect(collectionApi.addMember).toHaveBeenCalledWith(1, { username: 'new-user', role: 'editor' })
    expect(wrapper.text()).toContain('New User (new-user)')
  })

  it.each([
    [409, 'That user is already a member of this collection.'],
    [404, 'The collection or requested user is unavailable.'],
  ])('shows a safe member-add error for %s', async (status, message) => {
    vi.mocked(collectionApi.addMember).mockRejectedValue(new ApiError(status))
    const wrapper = await mountView('owner')
    const memberForm = wrapper.findAll('form').find((form) => form.text().includes('Add a member'))!

    await memberForm.get('input').setValue('target')
    await memberForm.trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain(message)
  })

  it('updates a member role without reloading the page', async () => {
    vi.mocked(collectionApi.updateMember).mockResolvedValue()
    const wrapper = await mountView('admin')

    await wrapper.get('.member-role select').setValue('editor')
    await flushPromises()

    expect(collectionApi.updateMember).toHaveBeenCalledWith(
      1,
      { id: 2, username: 'member', display_name: 'Member Name', role: 'viewer' },
      'editor',
    )
    expect(wrapper.get('.member-role select').element.value).toBe('editor')
  })

  it('confirms and removes a normal member', async () => {
    vi.mocked(collectionApi.deleteMember).mockResolvedValue()
    const wrapper = await mountView('admin')

    await wrapper.findAll('button').find((button) => button.text() === 'Remove')!.trigger('click')
    expect(wrapper.text()).toContain('Remove this member?')
    await wrapper.findAll('button').find((button) => button.text() === 'Confirm remove')!.trigger('click')
    await flushPromises()

    expect(collectionApi.deleteMember).toHaveBeenCalledWith(1, 2)
    expect(wrapper.text()).not.toContain('Member Name (member)')
  })

  it('confirms ownership transfer and refreshes ownership and role state', async () => {
    vi.mocked(collectionApi.transferOwnership).mockResolvedValue()
    const wrapper = await mountView('owner')
    vi.mocked(collectionApi.getCollection).mockResolvedValue({
      ...collection('admin'),
      owner: { id: 3, username: 'new-owner', display_name: 'New Owner' },
    })
    vi.mocked(collectionApi.listMembers).mockResolvedValue([
      { id: 1, username: 'owner', display_name: 'Collection Owner', role: 'admin' },
    ])
    const transferForm = wrapper.findAll('form').find((form) => form.text().includes('Review transfer'))!

    await transferForm.get('input').setValue(' new-owner ')
    await transferForm.trigger('submit.prevent')
    expect(collectionApi.transferOwnership).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('You will remain an admin member')
    await wrapper.findAll('button').find((button) => button.text() === 'Confirm transfer')!.trigger('click')
    await flushPromises()

    expect(collectionApi.transferOwnership).toHaveBeenCalledWith(1, 'new-owner')
    expect(wrapper.text()).toContain('Owner: New Owner (new-owner)')
    expect(wrapper.text()).toContain('admin')
    expect(wrapper.text()).not.toContain('Transfer ownership')
  })

  it.each([
    [409, 'You already own this collection.'],
    [403, 'You no longer have permission for this action.'],
    [404, 'The collection or requested user is unavailable.'],
  ])('shows a safe ownership-transfer error for %s', async (status, message) => {
    vi.mocked(collectionApi.transferOwnership).mockRejectedValue(new ApiError(status))
    const wrapper = await mountView('owner')
    const transferForm = wrapper.findAll('form').find((form) => form.text().includes('Review transfer'))!

    await transferForm.get('input').setValue('target')
    await transferForm.trigger('submit.prevent')
    await wrapper.findAll('button').find((button) => button.text() === 'Confirm transfer')!.trigger('click')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain(message)
  })

  it.each([
    [403, 'You do not have permission to open this collection.'],
    [404, 'This collection is no longer available to you.'],
  ])('shows a safe %s response state', async (status, message) => {
    vi.mocked(collectionApi.getCollection).mockRejectedValue(new ApiError(status))
    await router.push('/collections/1')
    const wrapper = mount(CollectionDetailView, { global: { plugins: [createPinia(), router] } })
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain(message)
  })
})
