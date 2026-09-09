import { ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError } from '@/api/client'
import * as api from '@/api/collections'

export const useCollectionsStore = defineStore('collections', () => {
  const collections = ref<api.CollectionSummary[]>([])
  const collection = ref<api.CollectionDetail | null>(null)
  const listLoading = ref(false)
  const detailLoading = ref(false)
  const listError = ref<ApiError | null>(null)
  const detailError = ref<ApiError | null>(null)

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
    try {
      collection.value = await api.getCollection(collectionId)
    } catch (error) {
      detailError.value = error instanceof ApiError ? error : new ApiError(0)
    } finally {
      detailLoading.value = false
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

  return {
    collections,
    collection,
    listLoading,
    detailLoading,
    listError,
    detailError,
    loadCollections,
    loadCollection,
    createCollection,
    updateCurrentCollection,
    deleteCurrentCollection,
  }
})
