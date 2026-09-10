import { ref } from 'vue'
import { defineStore } from 'pinia'
import { ApiError } from '@/api/client'
import * as api from '@/api/library'

export const useLibraryStore=defineStore('library',()=>{
  const titles=ref<api.LibraryTitleSummary[]>([]); const title=ref<api.LibraryTitleDetail|null>(null); const loading=ref(false); const error=ref<ApiError|null>(null)
  async function load(collectionId:number,filter:api.LibraryFilter={}){loading.value=true;error.value=null;try{titles.value=await api.listLibrary(collectionId,filter)}catch(e){error.value=e instanceof ApiError?e:new ApiError(0)}finally{loading.value=false}}
  async function loadDetail(collectionId:number,entryId:number){title.value=null;loading.value=true;error.value=null;try{title.value=await api.getLibraryTitle(collectionId,entryId)}catch(e){error.value=e instanceof ApiError?e:new ApiError(0)}finally{loading.value=false}}
  return {titles,title,loading,error,load,loadDetail}
})
