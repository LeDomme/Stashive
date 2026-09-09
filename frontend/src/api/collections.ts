import { request } from '@/api/client'

export type CollectionRole = 'owner' | 'admin' | 'editor' | 'viewer'

export interface CollectionSummary {
  id: number
  name: string
  type: string
  description: string | null
  role: CollectionRole
}

export interface CollectionOwner {
  id: number
  username: string
  display_name: string | null
}

export interface CollectionDetail extends CollectionSummary {
  owner: CollectionOwner
}

export interface CollectionMember {
  id: number
  username: string
  display_name: string | null
  role: Exclude<CollectionRole, 'owner'>
}

export interface CollectionCreatePayload {
  name: string
  type: string
  description: string | null
}

export interface CollectionUpdatePayload extends CollectionCreatePayload {}
export interface MemberPayload {
  username: string
  role: CollectionMember['role']
}

interface CollectionMutationResponse {
  id: number
  name: string
  role: CollectionRole
}

export const listCollections = (): Promise<CollectionSummary[]> => request('/api/collections')
export const getCollection = (collectionId: number): Promise<CollectionDetail> =>
  request(`/api/collections/${collectionId}`)
export const createCollection = (
  payload: CollectionCreatePayload,
): Promise<CollectionMutationResponse> =>
  request('/api/collections', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
export const updateCollection = (
  collectionId: number,
  payload: CollectionUpdatePayload,
): Promise<CollectionMutationResponse> =>
  request(`/api/collections/${collectionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
export const deleteCollection = (collectionId: number): Promise<void> =>
  request(`/api/collections/${collectionId}`, { method: 'DELETE' })
export const listMembers = (collectionId: number): Promise<CollectionMember[]> =>
  request(`/api/collections/${collectionId}/members`)
export const addMember = (collectionId: number, payload: MemberPayload): Promise<void> =>
  request(`/api/collections/${collectionId}/members`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
export const updateMember = (
  collectionId: number,
  member: CollectionMember,
  role: CollectionMember['role'],
): Promise<void> =>
  request(`/api/collections/${collectionId}/members/${member.id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: member.username, role }),
  })
export const deleteMember = (collectionId: number, memberId: number): Promise<void> =>
  request(`/api/collections/${collectionId}/members/${memberId}`, { method: 'DELETE' })
export const transferOwnership = (collectionId: number, username: string): Promise<void> =>
  request(`/api/collections/${collectionId}/transfer-ownership`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username }),
  })
