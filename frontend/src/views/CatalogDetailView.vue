<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useCatalogStore } from '@/stores/catalog'
import { useCollectionsStore } from '@/stores/collections'
const route=useRoute();const catalog=useCatalogStore();const collections=useCollectionsStore();const name=ref('');const id=()=>Number(route.params.collectionId);const entryId=()=>Number(route.params.entryId);const canEdit=computed(()=>['owner','admin','editor'].includes(collections.collection?.role??''))
async function load(){await collections.loadCollection(id());await catalog.loadDetail(id(),entryId())}watch(()=>route.params.entryId,load,{immediate:true})
async function add(){await catalog.createEdition(id(),entryId(),{display_name:name.value});name.value='';await catalog.loadDetail(id(),entryId())}
</script>
<template><section class="page-content"><RouterLink :to="{name:'catalog',params:{collectionId:id()}}">← Catalog</RouterLink><p v-if="catalog.loading">Loading…</p><div v-else-if="catalog.entry"><h1>{{catalog.entry.display_title}}</h1><p>{{catalog.entry.type}}</p><p v-if="catalog.entry.notes">{{catalog.entry.notes}}</p><h2>Editions</h2><ul><li v-for="edition in catalog.editions" :key="edition.id">{{edition.display_name}} <span v-if="edition.publisher">{{edition.publisher}}</span></li></ul><form v-if="canEdit" @submit.prevent="add"><label>Edition name<input v-model="name" required /></label><button>Add edition</button></form></div></section></template>
