import { ref } from 'vue'
import { defineStore } from 'pinia'
import { ApiError } from '@/api/client'
import * as api from '@/api/catalog'
export const useCatalogStore=defineStore('catalog',()=>{const entries=ref<api.CatalogEntry[]>([]);const entry=ref<api.CatalogEntry|null>(null);const editions=ref<api.Edition[]>([]);const loading=ref(false);const error=ref<ApiError|null>(null)
async function load(c:number){loading.value=true;error.value=null;try{entries.value=await api.listCatalog(c)}catch(e){error.value=e instanceof ApiError?e:new ApiError(0)}finally{loading.value=false}}
async function loadDetail(c:number,e:number){loading.value=true;error.value=null;try{[entry.value,editions.value]=await Promise.all([api.getCatalog(c,e),api.listEditions(c,e)])}catch(e){error.value=e instanceof ApiError?e:new ApiError(0)}finally{loading.value=false}}
return {entries,entry,editions,loading,error,load,loadDetail,...api}})
