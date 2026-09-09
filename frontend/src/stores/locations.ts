import { ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError } from '@/api/client'
import * as api from '@/api/locations'

export const useLocationsStore = defineStore('locations', () => {
  const tree = ref<api.LocationTreeNode[]>([])
  const loading = ref(false)
  const error = ref<ApiError | null>(null)

  async function loadTree(collectionId: number): Promise<void> {
    loading.value = true
    error.value = null
    try { tree.value = await api.listLocationTree(collectionId) }
    catch (cause) { error.value = cause instanceof ApiError ? cause : new ApiError(0) }
    finally { loading.value = false }
  }

  async function create(collectionId: number, payload: api.CreateLocationPayload): Promise<void> {
    await api.createLocation(collectionId, payload)
    await loadTree(collectionId)
  }
  async function update(collectionId: number, locationId: number, payload: api.UpdateLocationPayload): Promise<void> {
    await api.updateLocation(collectionId, locationId, payload)
    await loadTree(collectionId)
  }
  async function remove(collectionId: number, locationId: number): Promise<void> {
    await api.deleteLocation(collectionId, locationId)
    await loadTree(collectionId)
  }
  return { tree, loading, error, loadTree, create, update, remove }
})
