import { request } from '@/api/client'

export type LocationType = 'room' | 'cabinet' | 'shelf' | 'box' | 'drawer' | 'other'

export interface LocationTreeNode {
  id: number
  collection_id: number
  parent_id: number | null
  name: string
  type: LocationType
  description: string | null
  children: LocationTreeNode[]
}

export interface CreateLocationPayload {
  name: string
  type: LocationType
  description?: string | null
  parent_id?: number | null
}

export interface UpdateLocationPayload {
  name?: string
  type?: LocationType
  description?: string | null
  parent_id?: number | null
}

export const listLocationTree = (collectionId: number): Promise<LocationTreeNode[]> =>
  request(`/api/collections/${collectionId}/locations`)

export const createLocation = (collectionId: number, payload: CreateLocationPayload): Promise<LocationTreeNode> =>
  request(`/api/collections/${collectionId}/locations`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  })

export const updateLocation = (
  collectionId: number, locationId: number, payload: UpdateLocationPayload,
): Promise<LocationTreeNode> => request(`/api/collections/${collectionId}/locations/${locationId}`, {
  method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
})

export const deleteLocation = (collectionId: number, locationId: number): Promise<void> =>
  request(`/api/collections/${collectionId}/locations/${locationId}`, { method: 'DELETE' })
