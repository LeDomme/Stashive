<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import type { CollectionCreatePayload } from '@/api/collections'
import { useCollectionsStore } from '@/stores/collections'

const collections = useCollectionsStore()
const router = useRouter()
const name = ref('')
const description = ref('')
const type = ref('movies')
const createError = ref(false)
const creating = ref(false)

const hasCollections = computed(() => collections.collections.length > 0)

onMounted(() => collections.loadCollections())

async function createCollection(): Promise<void> {
  creating.value = true
  createError.value = false
  const payload: CollectionCreatePayload = {
    name: name.value.trim(),
    type: type.value,
    description: description.value.trim() || null,
  }
  try {
    const collectionId = await collections.createCollection(payload)
    await router.push({ name: 'collection-detail', params: { collectionId } })
  } catch {
    createError.value = true
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <section class="page-content" aria-labelledby="collections-heading">
    <div class="page-heading">
      <div>
        <p class="eyebrow">Collections</p>
        <h1 id="collections-heading">Your collections</h1>
        <p>Keep each physical collection separate, share it when you need to, and stay organized.</p>
      </div>
    </div>

    <form class="collection-form panel" @submit.prevent="createCollection">
      <h2>Create a collection</h2>
      <label>
        Name
        <input v-model="name" required maxlength="255" autocomplete="off" />
      </label>
      <label>
        Collection type
        <select v-model="type">
          <option value="movies">Movies</option>
          <option value="board_games">Board games</option>
        </select>
      </label>
      <label>
        Description <span class="optional">optional</span>
        <textarea v-model="description" rows="3" maxlength="2000" />
      </label>
      <p v-if="createError" class="form-error" role="alert">
        The collection could not be created. Please try again.
      </p>
      <button type="submit" :disabled="creating">{{ creating ? 'Creating…' : 'Create collection' }}</button>
    </form>

    <p v-if="collections.listLoading" class="state-message" role="status">Loading collections…</p>
    <p v-else-if="collections.listError" class="state-message state-error" role="alert">
      Collections could not be loaded. Please try again.
    </p>
    <div v-else-if="!hasCollections" class="empty-state">
      <h2>No collections yet</h2>
      <p>Create your first collection to start organizing what you own.</p>
    </div>
    <ul v-else class="collection-list" aria-label="Collections">
      <li v-for="collection in collections.collections" :key="collection.id" class="collection-card">
        <RouterLink :to="{ name: 'collection-detail', params: { collectionId: collection.id } }">
          <span class="collection-card__role">{{ collection.role }}</span>
          <h2>{{ collection.name }}</h2>
          <p>{{ collection.description || 'No description yet.' }}</p>
          <span class="collection-card__link">Open collection →</span>
        </RouterLink>
      </li>
    </ul>
  </section>
</template>
