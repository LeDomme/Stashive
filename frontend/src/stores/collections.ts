import { ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError } from '@/api/client'
import * as api from '@/api/collections'

export const useCollectionsStore = defineStore('collections', () => {
  const collections = ref<api.CollectionSummary[]>([])
  const collection = ref<api.CollectionDetail | null>(null)
  const members = ref<api.CollectionMember[]>([])
  const listLoading = ref(false)
  const detailLoading = ref(false)
  const listError = ref<ApiError | null>(null)
  const detailError = ref<ApiError | null>(null)
  const membersError = ref<ApiError | null>(null)

  async function loadCollections(): Promise<void> {
    listLoading.value = true
    listError.value = null
    try {
      collections.value = await api.listCollections()
    } catch (error) {
      listError.value = error instanceof ApiError ? error : new ApiError(0)
    } finally {
      listLoading.value = false
    }
  }

  async function loadCollection(collectionId: number): Promise<void> {
    detailLoading.value = true
    detailError.value = null
    collection.value = null
    members.value = []
    try {
      collection.value = await api.getCollection(collectionId)
    } catch (error) {
      detailError.value = error instanceof ApiError ? error : new ApiError(0)
    } finally {
      detailLoading.value = false
    }
  }

  async function loadMembers(collectionId: number): Promise<void> {
    membersError.value = null
    try {
      members.value = await api.listMembers(collectionId)
    } catch (error) {
      membersError.value = error instanceof ApiError ? error : new ApiError(0)
    }
  }

  async function createCollection(payload: api.CollectionCreatePayload): Promise<number> {
    const created = await api.createCollection(payload)
    return created.id
  }

  async function updateCurrentCollection(payload: api.CollectionUpdatePayload): Promise<void> {
    if (!collection.value) return
    await api.updateCollection(collection.value.id, payload)
    collection.value = { ...collection.value, ...payload }
  }

  async function deleteCurrentCollection(): Promise<void> {
    if (!collection.value) return
    await api.deleteCollection(collection.value.id)
    collection.value = null
  }

  async function addCollectionMember(
    collectionId: number,
    payload: api.MemberPayload,
  ): Promise<void> {
    await api.addMember(collectionId, payload)
    await loadMembers(collectionId)
  }

  async function updateCollectionMember(
    collectionId: number,
    member: api.CollectionMember,
    role: api.CollectionMember['role'],
  ): Promise<void> {
    await api.updateMember(collectionId, member, role)
    members.value = members.value.map((item) => (item.id === member.id ? { ...item, role } : item))
  }

  async function deleteCollectionMember(collectionId: number, memberId: number): Promise<void> {
    await api.deleteMember(collectionId, memberId)
    members.value = members.value.filter((member) => member.id !== memberId)
  }

  async function transferCurrentOwnership(username: string): Promise<void> {
    if (!collection.value) return
    const collectionId = collection.value.id
    await api.transferOwnership(collectionId, username)
    await loadCollection(collectionId)
    if (collection.value && ['owner', 'admin'].includes(collection.value.role)) {
      await loadMembers(collectionId)
    }
  }

  return {
    collections,
    collection,
    members,
    listLoading,
    detailLoading,
    listError,
    detailError,
    membersError,
    loadCollections,
    loadCollection,
    loadMembers,
    createCollection,
    updateCurrentCollection,
    deleteCurrentCollection,
    addCollectionMember,
    updateCollectionMember,
    deleteCollectionMember,
    transferCurrentOwnership,
  }
})
