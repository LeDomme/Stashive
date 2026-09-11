<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useCatalogStore } from '@/stores/catalog'
import { useCollectionsStore } from '@/stores/collections'

const route = useRoute()
const router = useRouter()
const catalog = useCatalogStore()
const collections = useCollectionsStore()
const title = ref('')
const type = ref('')
const creating = ref(false)
const canEdit = computed(() => ['owner', 'admin', 'editor'].includes(collections.collection?.role ?? ''))
const id = () => Number(route.params.collectionId)

async function load() {
  await collections.loadCollection(id())
  await catalog.load(id())
}

watch(() => route.params.collectionId, load, { immediate: true })

async function create() {
  const entry = await catalog.createCatalog(id(), { display_title: title.value, type: type.value })
  await router.push({ name: 'catalog-detail', params: { collectionId: id(), entryId: entry.id } })
}
</script>

<template>
  <section class="page-content workspace-content">
    <div class="page-heading">
      <div>
        <p v-if="collections.collection" class="eyebrow">{{ collections.collection.name }}</p>
        <h1>Advanced catalog</h1>
        <p>Low-level view of titles, editions and IDs. For normal collection management, use Inventory.</p>
      </div>
      <button v-if="canEdit" @click="creating = true">New catalog entry</button>
    </div>

    <nav class="collection-nav" aria-label="Collection navigation">
      <RouterLink :to="{ name: 'inventory', params: { collectionId: id() } }">Inventory</RouterLink>
      <RouterLink :to="{ name: 'locations', params: { collectionId: id() } }">Locations</RouterLink>
      <RouterLink :to="{ name: 'collection-settings', params: { collectionId: id() } }">Settings</RouterLink>
    </nav>

    <p v-if="catalog.error" class="form-error" role="alert">Catalog unavailable.</p>
    <template v-else>
      <form v-if="creating" class="collection-form panel modal-panel" @submit.prevent="create">
        <h2>New catalog entry</h2>
        <label>Display title<input v-model="title" required /></label>
        <label>Type<input v-model="type" required /></label>
        <div class="action-row">
          <button>Create entry</button>
          <button type="button" class="button-secondary" @click="creating = false">Cancel</button>
        </div>
      </form>
      <div v-if="!catalog.entries.length" class="empty-state">
        <h2>No catalog entries yet</h2>
        <p>Create a title to add its editions and physical copies.</p>
      </div>
      <ul v-else class="catalog-list">
        <li v-for="entry in catalog.entries" :key="entry.id" class="catalog-card">
          <RouterLink :to="{ name: 'catalog-detail', params: { collectionId: id(), entryId: entry.id } }">
            <span>{{ entry.type }}</span>
            <h2>{{ entry.display_title }}</h2>
            <span>Open catalog entry →</span>
          </RouterLink>
        </li>
      </ul>
    </template>
  </section>
</template>
