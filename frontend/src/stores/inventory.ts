import { ref } from 'vue'
import { defineStore } from 'pinia'
import { ApiError } from '@/api/client'
import * as api from '@/api/inventory'
export const useInventoryStore=defineStore('inventory',()=>{const items=ref<api.InventoryItem[]>([]);const item=ref<api.InventoryItem|null>(null);const loading=ref(false);const error=ref<ApiError|null>(null)
async function load(collectionId:number){loading.value=true;error.value=null;try{items.value=await api.listInventory(collectionId)}catch(cause){error.value=cause instanceof ApiError?cause:new ApiError(0)}finally{loading.value=false}}
async function loadItem(collectionId:number,itemId:number){loading.value=true;error.value=null;try{item.value=await api.getInventoryItem(collectionId,itemId)}catch(cause){error.value=cause instanceof ApiError?cause:new ApiError(0)}finally{loading.value=false}}
return {items,item,loading,error,load,loadItem,...api}})
