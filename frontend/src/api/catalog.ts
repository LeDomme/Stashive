import { request } from '@/api/client'

export interface CatalogEntry { id:number; collection_id:number; display_title:string; type:string; sort_title:string|null; notes:string|null }
export interface Edition { id:number; catalog_entry_id:number; display_name:string; media_format:string|null; release_date:string|null; publisher:string|null; region:string|null; language:string|null }
export interface Identifier { id:number; edition_id:number; type:string; value:string; source:string|null }
export type CatalogPayload = Partial<Pick<CatalogEntry, 'display_title'|'type'|'sort_title'|'notes'>>
export type EditionPayload = Partial<Pick<Edition, 'display_name'|'media_format'|'release_date'|'publisher'|'region'|'language'>>
export type IdentifierPayload = Partial<Pick<Identifier, 'type'|'value'|'source'>>
const json = <T>(path:string, method:string, body?:object) => request<T>(path,{method,headers:{'Content-Type':'application/json'},body:body ? JSON.stringify(body):undefined})
export const listCatalog=(c:number)=>request<CatalogEntry[]>(`/api/collections/${c}/catalog-entries`)
export const getCatalog=(c:number,e:number)=>request<CatalogEntry>(`/api/collections/${c}/catalog-entries/${e}`)
export const createCatalog=(c:number,p:CatalogPayload)=>json<CatalogEntry>(`/api/collections/${c}/catalog-entries`,'POST',p)
export const updateCatalog=(c:number,e:number,p:CatalogPayload)=>json<CatalogEntry>(`/api/collections/${c}/catalog-entries/${e}`,'PATCH',p)
export const deleteCatalog=(c:number,e:number)=>json<void>(`/api/collections/${c}/catalog-entries/${e}`,'DELETE')
export const listEditions=(c:number,e:number)=>request<Edition[]>(`/api/collections/${c}/catalog-entries/${e}/editions`)
export const createEdition=(c:number,e:number,p:EditionPayload)=>json<Edition>(`/api/collections/${c}/catalog-entries/${e}/editions`,'POST',p)
export const updateEdition=(c:number,e:number,p:EditionPayload)=>json<Edition>(`/api/collections/${c}/editions/${e}`,'PATCH',p)
export const deleteEdition=(c:number,e:number)=>json<void>(`/api/collections/${c}/editions/${e}`,'DELETE')
export const listIdentifiers=(c:number,e:number)=>request<Identifier[]>(`/api/collections/${c}/editions/${e}/identifiers`)
export const createIdentifier=(c:number,e:number,p:IdentifierPayload)=>json<Identifier>(`/api/collections/${c}/editions/${e}/identifiers`,'POST',p)
export const updateIdentifier=(c:number,e:number,i:number,p:IdentifierPayload)=>json<Identifier>(`/api/collections/${c}/editions/${e}/identifiers/${i}`,'PATCH',p)
export const deleteIdentifier=(c:number,e:number,i:number)=>json<void>(`/api/collections/${c}/editions/${e}/identifiers/${i}`,'DELETE')
