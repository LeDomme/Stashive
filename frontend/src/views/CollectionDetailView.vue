<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import type { CollectionUpdatePayload } from '@/api/collections'
import { useCollectionsStore } from '@/stores/collections'

const route = useRoute()
const router = useRouter()
const collections = useCollectionsStore()
const editing = ref(false)
const saving = ref(false)
const saveError = ref(false)
const confirmingDelete = ref(false)
const deleting = ref(false)
const deleteError = ref(false)
const name = ref('')
const description = ref('')
const type = ref('movies')

const canEdit = computed(() => ['owner', 'admin'].includes(collections.collection?.role ?? ''))
const canDelete = computed(() => collections.collection?.role === 'owner')

function collectionIdFromRoute(): number {
  return Number(route.params.collectionId)
}

async function loadCollection(): Promise<void> {
  editing.value = false
  confirmingDelete.value = false
  await collections.loadCollection(collectionIdFromRoute())
  if (collections.collection) {
    name.value = collections.collection.name
    description.value = collections.collection.description ?? ''
    type.value = collections.collection.type
  }
}

watch(() => route.params.collectionId, loadCollection, { immediate: true })

function beginEditing(): void {
  if (!collections.collection) return
  name.value = collections.collection.name
  description.value = collections.collection.description ?? ''
  type.value = collections.collection.type
  saveError.value = false
  editing.value = true
}

async function saveCollection(): Promise<void> {
  saving.value = true
  saveError.value = false
  const payload: CollectionUpdatePayload = {
    name: name.value.trim(),
    type: type.value,
    description: description.value.trim() || null,
  }
  try {
    await collections.updateCurrentCollection(payload)
    editing.value = false
  } catch {
    saveError.value = true
  } finally {
    saving.value = false
  }
}

async function removeCollection(): Promise<void> {
  deleting.value = true
  deleteError.value = false
  try {
    await collections.deleteCurrentCollection()
    await router.push({ name: 'collections' })
  } catch {
    deleteError.value = true
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <section class="page-content" aria-labelledby="collection-heading">
    <RouterLink class="back-link" :to="{ name: 'collections' }">← All collections</RouterLink>
    <p v-if="collections.detailLoading" class="state-message" role="status">Loading collection…</p>
    <div v-else-if="collections.detailError" class="empty-state state-error" role="alert">
      <h1>Collection unavailable</h1>
      <p v-if="collections.detailError.status === 403">You do not have permission to open this collection.</p>
      <p v-else-if="collections.detailError.status === 404">This collection is no longer available to you.</p>
      <p v-else>We could not load this collection. Please try again.</p>
    </div>
    <template v-else-if="collections.collection">
      <div class="page-heading detail-heading">
        <div>
          <p class="eyebrow">Collection <span class="role-pill">{{ collections.collection.role }}</span></p>
          <h1 id="collection-heading">{{ collections.collection.name }}</h1>
          <p>{{ collections.collection.description || 'No description yet.' }}</p>
        </div>
        <div v-if="canEdit" class="action-row">
          <button type="button" class="button-secondary" @click="beginEditing">Edit details</button>
          <button v-if="canDelete" type="button" class="button-danger" @click="confirmingDelete = true">
            Delete collection
          </button>
        </div>
      </div>

      <dl class="metadata-grid panel">
        <div><dt>Type</dt><dd>{{ collections.collection.type === 'movies' ? 'Movies' : collections.collection.type }}</dd></div>
        <div><dt>Your role</dt><dd>{{ collections.collection.role }}</dd></div>
      </dl>

      <form v-if="editing" class="collection-form panel" @submit.prevent="saveCollection">
        <h2>Edit collection details</h2>
        <label>Name<input v-model="name" required maxlength="255" /></label>
        <label>Collection type<select v-model="type"><option value="movies">Movies</option><option value="board_games">Board games</option></select></label>
        <label>Description <span class="optional">optional</span><textarea v-model="description" rows="3" maxlength="2000" /></label>
        <p v-if="saveError" class="form-error" role="alert">Changes could not be saved. Please try again.</p>
        <div class="action-row"><button type="submit" :disabled="saving">{{ saving ? 'Saving…' : 'Save changes' }}</button><button type="button" class="button-secondary" @click="editing = false">Cancel</button></div>
      </form>

      <section v-if="confirmingDelete" class="confirmation panel" aria-labelledby="delete-heading">
        <h2 id="delete-heading">Delete {{ collections.collection.name }}?</h2>
        <p>This permanently removes the collection and its related data. This cannot be undone.</p>
        <p v-if="deleteError" class="form-error" role="alert">The collection could not be deleted. Please try again.</p>
        <div class="action-row"><button type="button" class="button-danger" :disabled="deleting" @click="removeCollection">{{ deleting ? 'Deleting…' : 'Confirm delete' }}</button><button type="button" class="button-secondary" :disabled="deleting" @click="confirmingDelete = false">Cancel</button></div>
      </section>
    </template>
  </section>
</template>
