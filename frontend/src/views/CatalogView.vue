<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCatalogStore } from '@/stores/catalog'
import { useCollectionsStore } from '@/stores/collections'
const route=useRoute(); const router=useRouter(); const catalog=useCatalogStore(); const collections=useCollectionsStore()
const title=ref('');const type=ref('');const canEdit=computed(()=>['owner','admin','editor'].includes(collections.collection?.role??''));const id=()=>Number(route.params.collectionId)
async function load(){await collections.loadCollection(id());await catalog.load(id())} watch(()=>route.params.collectionId,load,{immediate:true})
async function create(){const entry=await catalog.createCatalog(id(),{display_title:title.value,type:type.value});await router.push({name:'catalog-detail',params:{collectionId:id(),entryId:entry.id}})}
</script>
<template><section class="page-content"><RouterLink class="back-link" :to="{name:'collection-detail',params:{collectionId:id()}}">← Collection</RouterLink><h1>Catalog</h1><p v-if="catalog.loading">Loading…</p><p v-else-if="catalog.error" class="form-error">Catalog unavailable.</p><template v-else><p v-if="!catalog.entries.length">No catalog entries yet.</p><ul><li v-for="entry in catalog.entries" :key="entry.id"><RouterLink :to="{name:'catalog-detail',params:{collectionId:id(),entryId:entry.id}}">{{entry.display_title}}</RouterLink> — {{entry.type}}</li></ul><form v-if="canEdit" @submit.prevent="create"><label>Display title<input v-model="title" required /></label><label>Type<input v-model="type" required /></label><button>Create entry</button></form></template></section></template>
