<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError } from '@/api/client'
import type { LocationTreeNode } from '@/api/locations'
import PresetCustomField from '@/components/PresetCustomField.vue'
import { CONDITION_PRESETS } from '@/constants/inventoryPresets'
import { useCollectionsStore } from '@/stores/collections'
import { useLibraryStore } from '@/stores/library'
import { useLocationsStore } from '@/stores/locations'

const route = useRoute()
const router = useRouter()
const collections = useCollectionsStore()
const library = useLibraryStore()
const locations = useLocationsStore()
const error = ref('')
const busy = ref(false)
const form = ref({ condition: '', notes: '', location_id: '' })
const collectionId = computed(() => Number(route.params.collectionId))
const entryId = computed(() => Number(route.params.catalogEntryId))
const editionId = computed(() => Number(route.params.editionId))
const canEdit = computed(() => ['owner', 'admin', 'editor'].includes(collections.collection?.role ?? ''))
const edition = computed(() => library.title?.editions.find((candidate) => candidate.id === editionId.value) ?? null)
const locationOptions = computed(() => flatten(locations.tree))

function flatten(nodes: LocationTreeNode[], prefix = ''): { id: number; path: string }[] {
  return nodes.flatMap((node) => {
    const path = prefix ? `${prefix} > ${node.name}` : node.name
    return [{ id: node.id, path }, ...flatten(node.children, path)]
  })
}
function detailRoute() { return { name: 'inventory-title', params: { collectionId: collectionId.value, catalogEntryId: entryId.value } } }
function message(cause: unknown) {
  if (cause instanceof ApiError && cause.status === 403) return 'You do not have permission to add a physical copy.'
  if (cause instanceof ApiError && cause.status === 404) return 'This edition is not available.'
  if (cause instanceof ApiError && cause.status === 422) return 'Check the physical copy details.'
  return 'This physical copy could not be added. Please try again.'
}
async function load() {
  error.value = ''
  await collections.loadCollection(collectionId.value)
  if (!canEdit.value) return
  await Promise.all([library.loadDetail(collectionId.value, entryId.value), locations.loadTree(collectionId.value)])
  if (!edition.value) error.value = 'This edition is not available.'
}
async function save() {
  if (!edition.value) return
  busy.value = true
  error.value = ''
  try {
    await library.addItem(collectionId.value, {
      title: { existing_id: entryId.value, new: null },
      edition: { existing_id: editionId.value, new: null },
      copy: { condition: form.value.condition || null, notes: form.value.notes || null, location_id: Number(form.value.location_id) || null },
    })
    await Promise.all([library.loadDetail(collectionId.value, entryId.value), library.load(collectionId.value)])
    await router.push(detailRoute())
  } catch (cause) { error.value = message(cause) } finally { busy.value = false }
}
watch(() => [route.params.collectionId, route.params.catalogEntryId, route.params.editionId], load, { immediate: true })
</script>

<template>
  <section class="page-content workspace-content">
    <RouterLink class="back-link" :to="detailRoute()">Back to title</RouterLink>
    <p v-if="!canEdit && collections.collection" class="form-error" role="alert">You do not have permission to add a physical copy.</p>
    <template v-else-if="edition">
      <p class="eyebrow">{{ library.title?.catalog_entry.display_title }} · {{ edition.display_name }}<span v-if="edition.media_format"> · {{ edition.media_format }}</span></p>
      <h1>Add physical copy</h1>
      <form class="collection-form panel" @submit.prevent="save">
        <PresetCustomField id="copy-condition" v-model="form.condition" label="Condition" :presets="CONDITION_PRESETS" allow-empty empty-value="" />
        <label>Location <span class="optional">optional</span><select v-model="form.location_id"><option value="">Unassigned</option><option v-for="location in locationOptions" :key="location.id" :value="String(location.id)">{{ location.path }}</option></select></label>
        <label>Notes <span class="optional">optional</span><textarea v-model="form.notes" /></label>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <div class="action-row"><button :disabled="busy">{{ busy ? 'Adding…' : 'Add physical copy' }}</button><RouterLink class="button-secondary button-link" :to="detailRoute()">Cancel</RouterLink></div>
      </form>
    </template>
    <p v-else-if="error" class="form-error" role="alert">{{ error }}</p>
  </section>
</template>
