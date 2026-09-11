import { ref } from 'vue'
import { defineStore } from 'pinia'
import { ApiError } from '@/api/client'
import * as api from '@/api/library'

export const useLibraryStore=defineStore('library',()=>{
  const titles=ref<api.LibraryTitleSummary[]>([]); const title=ref<api.LibraryTitleDetail|null>(null); const searchResults=ref<api.LibraryTitleSummary[]>([]); const loading=ref(false); const error=ref<ApiError|null>(null); let searchRequest=0
  async function load(collectionId:number,filter:api.LibraryFilter={}){loading.value=true;error.value=null;try{titles.value=await api.listLibrary(collectionId,filter)}catch(e){error.value=e instanceof ApiError?e:new ApiError(0)}finally{loading.value=false}}
  async function loadDetail(collectionId:number,entryId:number){title.value=null;loading.value=true;error.value=null;try{title.value=await api.getLibraryTitle(collectionId,entryId)}catch(e){error.value=e instanceof ApiError?e:new ApiError(0)}finally{loading.value=false}}
  async function searchTitles(collectionId:number,query:string){const request=++searchRequest;error.value=null;if(query.trim().length<2){searchResults.value=[];return []}try{const results=await api.searchTitles(collectionId,query);if(request===searchRequest)searchResults.value=results;return results}catch(e){if(request===searchRequest)error.value=e instanceof ApiError?e:new ApiError(0);throw e}}
  async function addItem(collectionId:number,payload:api.AddItemPayload){return api.addItem(collectionId,payload)}
  return {titles,title,searchResults,loading,error,load,loadDetail,searchTitles,addItem}
})
