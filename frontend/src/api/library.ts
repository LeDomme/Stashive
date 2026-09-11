import { request } from '@/api/client'
import type { CatalogEntry, Edition, Identifier } from '@/api/catalog'
import type { InventoryItem } from '@/api/inventory'

export interface LibraryTitleSummary { id:number; catalog_entry_id:number; display_title:string; sort_title:string|null; type:string; edition_count:number; copy_count:number; media_formats:string[] }
export interface LibraryEdition extends Edition { identifiers: Identifier[]; copies: InventoryItem[] }
export interface LibraryTitleDetail { catalog_entry: CatalogEntry; editions: LibraryEdition[] }
export interface AddItemChoice<T> { existing_id: number | null; new: T | null }
export interface AddItemPayload {
  title: AddItemChoice<Pick<CatalogEntry, 'display_title' | 'sort_title' | 'type' | 'notes'>>
  edition: AddItemChoice<Pick<Edition, 'display_name' | 'media_format' | 'release_date' | 'publisher' | 'region' | 'language'>>
  copy: { condition: string | null; notes: string | null; location_id: number | null }
}
export interface AddItemResponse { catalog_entry_id: number; edition_id: number; inventory_item_id: number }
export interface LibraryFilter { locationId?: number; includeDescendants?: boolean; unassigned?: boolean }
export const listLibrary=(collectionId:number,filter:LibraryFilter={})=>{const query=new URLSearchParams();if(filter.unassigned)query.set('unassigned','true');else if(filter.locationId){query.set('location_id',String(filter.locationId));if(filter.includeDescendants===false)query.set('include_descendants','false')}const suffix=query.size?`?${query}`:'';return request<LibraryTitleSummary[]>(`/api/collections/${collectionId}/library${suffix}`)}
export const getLibraryTitle=(collectionId:number,entryId:number)=>request<LibraryTitleDetail>(`/api/collections/${collectionId}/library/${entryId}`)
export const searchTitles=(collectionId:number,query:string)=>request<LibraryTitleSummary[]>(`/api/collections/${collectionId}/library/title-search?q=${encodeURIComponent(query)}`)
export const addItem=(collectionId:number,payload:AddItemPayload)=>request<AddItemResponse>(`/api/collections/${collectionId}/items`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
