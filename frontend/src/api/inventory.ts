import { request } from '@/api/client'

export interface InventoryItem { id:number; edition_id:number; condition:string|null; notes:string|null; location_id:number|null; created_at:string; updated_at:string }
export type InventoryItemPayload = Partial<Pick<InventoryItem, 'edition_id'|'condition'|'notes'>>
const json=<T>(path:string,method:string,body?:object)=>request<T>(path,{method,headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined})
export const listInventory=(collectionId:number)=>request<InventoryItem[]>(`/api/collections/${collectionId}/inventory-items`)
export const getInventoryItem=(collectionId:number,itemId:number)=>request<InventoryItem>(`/api/collections/${collectionId}/inventory-items/${itemId}`)
export const createInventoryItem=(collectionId:number,payload:InventoryItemPayload)=>json<InventoryItem>(`/api/collections/${collectionId}/inventory-items`,'POST',payload)
export const updateInventoryItem=(collectionId:number,itemId:number,payload:InventoryItemPayload)=>json<InventoryItem>(`/api/collections/${collectionId}/inventory-items/${itemId}`,'PATCH',payload)
export const deleteInventoryItem=(collectionId:number,itemId:number)=>json<void>(`/api/collections/${collectionId}/inventory-items/${itemId}`,'DELETE')
