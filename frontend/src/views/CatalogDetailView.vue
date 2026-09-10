<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError } from '@/api/client'
import type { Edition, Identifier } from '@/api/catalog'
import { useCatalogStore } from '@/stores/catalog'
import { useCollectionsStore } from '@/stores/collections'

const route = useRoute()
const router = useRouter()
const catalog = useCatalogStore()
const collections = useCollectionsStore()
const name = ref('')
const title = ref('')
const type = ref('')
const sortTitle = ref('')
const notes = ref('')
const editing = ref(false)
const editingEdition = ref<number | null>(null)
const confirmingEdition = ref<number | null>(null)
const deleteBusy = ref(false)
const editionForm = ref({ display_name: '', release_date: '', publisher: '', region: '', language: '' })
const identifiers = ref<Record<number, Identifier[]>>({})
const addingIdentifier = ref<number | null>(null)
const editingIdentifier = ref<number | null>(null)
const confirmingIdentifier = ref<number | null>(null)
const identifierForm = ref({ type: '', value: '', source: '' })
const confirming = ref(false)
const error = ref('')

const id = () => Number(route.params.collectionId)
const entryId = () => Number(route.params.entryId)
const canEdit = computed(() => ['owner', 'admin', 'editor'].includes(collections.collection?.role ?? ''))

async function loadIdentifiers() {
  const editionIdentifiers = await Promise.all(catalog.editions.map(async (edition) => [edition.id, await catalog.listIdentifiers(id(), edition.id)] as const))
  identifiers.value = Object.fromEntries(editionIdentifiers)
}

async function load() {
  await collections.loadCollection(id())
  await catalog.loadDetail(id(), entryId())
  try {
    await loadIdentifiers()
  } catch (cause) {
    error.value = message(cause)
  }
}

watch(() => route.params.entryId, load, { immediate: true })

async function add() {
  await catalog.createEdition(id(), entryId(), { display_name: name.value })
  name.value = ''
  await catalog.loadDetail(id(), entryId())
  await loadIdentifiers()
}

function beginEditionEdit(edition: Edition) {
  editingEdition.value = edition.id
  editionForm.value = {
    display_name: edition.display_name,
    release_date: edition.release_date ?? '',
    publisher: edition.publisher ?? '',
    region: edition.region ?? '',
    language: edition.language ?? '',
  }
}

async function saveEdition(editionId: number) {
  if (!editionForm.value.display_name.trim()) {
    error.value = 'Edition name is required.'
    return
  }
  try {
    await catalog.updateEdition(id(), editionId, {
      display_name: editionForm.value.display_name.trim(),
      release_date: editionForm.value.release_date || null,
      publisher: editionForm.value.publisher || null,
      region: editionForm.value.region || null,
      language: editionForm.value.language || null,
    })
    await catalog.loadDetail(id(), entryId())
    editingEdition.value = null
  } catch (cause) {
    error.value = message(cause)
  }
}

async function confirmEditionDelete() {
  if (confirmingEdition.value === null) return
  deleteBusy.value = true
  try {
    await catalog.deleteEdition(id(), confirmingEdition.value)
    await catalog.loadDetail(id(), entryId())
    await loadIdentifiers()
    confirmingEdition.value = null
  } catch (cause) {
    error.value = message(cause)
  } finally {
    deleteBusy.value = false
  }
}

function beginIdentifierAdd(editionId: number) {
  error.value = ''
  editingIdentifier.value = null
  confirmingIdentifier.value = null
  addingIdentifier.value = editionId
  identifierForm.value = { type: '', value: '', source: '' }
}

function beginIdentifierEdit(identifier: Identifier) {
  error.value = ''
  addingIdentifier.value = null
  confirmingIdentifier.value = null
  editingIdentifier.value = identifier.id
  identifierForm.value = { type: identifier.type, value: identifier.value, source: identifier.source ?? '' }
}

function beginIdentifierDelete(identifierId: number) {
  error.value = ''
  addingIdentifier.value = null
  editingIdentifier.value = null
  confirmingIdentifier.value = identifierId
}

function validIdentifier() {
  if (!identifierForm.value.type.trim() || !identifierForm.value.value.trim()) {
    error.value = 'Identifier type and value are required.'
    return false
  }
  return true
}

async function createIdentifier(editionId: number) {
  if (!validIdentifier()) return
  try {
    const identifier = await catalog.createIdentifier(id(), editionId, {
      type: identifierForm.value.type.trim(),
      value: identifierForm.value.value.trim(),
      source: identifierForm.value.source.trim() || null,
    })
    identifiers.value = { ...identifiers.value, [editionId]: [...(identifiers.value[editionId] ?? []), identifier] }
    addingIdentifier.value = null
    identifierForm.value = { type: '', value: '', source: '' }
  } catch (cause) {
    error.value = identifierMessage(cause)
  }
}

async function saveIdentifier(editionId: number, identifierId: number) {
  if (!validIdentifier()) return
  try {
    const updated = await catalog.updateIdentifier(id(), editionId, identifierId, {
      type: identifierForm.value.type.trim(),
      value: identifierForm.value.value.trim(),
      source: identifierForm.value.source.trim() || null,
    })
    identifiers.value = {
      ...identifiers.value,
      [editionId]: (identifiers.value[editionId] ?? []).map((identifier) => identifier.id === identifierId ? updated : identifier),
    }
    editingIdentifier.value = null
  } catch (cause) {
    error.value = identifierMessage(cause)
  }
}

async function confirmIdentifierDelete(editionId: number, identifierId: number) {
  try {
    await catalog.deleteIdentifier(id(), editionId, identifierId)
    identifiers.value = {
      ...identifiers.value,
      [editionId]: (identifiers.value[editionId] ?? []).filter((identifier) => identifier.id !== identifierId),
    }
    confirmingIdentifier.value = null
  } catch (cause) {
    error.value = identifierMessage(cause)
  }
}

function beginEdit() {
  if (!catalog.entry) return
  title.value = catalog.entry.display_title
  type.value = catalog.entry.type
  sortTitle.value = catalog.entry.sort_title ?? ''
  notes.value = catalog.entry.notes ?? ''
  error.value = ''
  editing.value = true
}

function message(cause: unknown) {
  if (cause instanceof ApiError) {
    if (cause.status === 403) return 'You do not have permission for this action.'
    if (cause.status === 404) return 'This catalog entry is no longer available.'
    if (cause.status === 409) return 'This change conflicts with existing data.'
    if (cause.status === 422) return 'Check the entered catalog entry details.'
  }
  return 'This action could not be completed. Please try again.'
}

function identifierMessage(cause: unknown) {
  if (cause instanceof ApiError) {
    if (cause.status === 403) return 'You do not have permission for this action.'
    if (cause.status === 404) return 'This identifier is no longer available.'
    if (cause.status === 409) return 'This identifier already exists for this edition.'
    if (cause.status === 422) return 'Check the entered identifier details.'
  }
  return 'This action could not be completed. Please try again.'
}

async function save() {
  if (!title.value.trim()) {
    error.value = 'Display title is required.'
    return
  }
  try {
    await catalog.updateCatalog(id(), entryId(), { display_title: title.value.trim(), type: type.value, sort_title: sortTitle.value.trim() || null, notes: notes.value.trim() || null })
    await catalog.loadDetail(id(), entryId())
    editing.value = false
  } catch (cause) {
    error.value = message(cause)
  }
}

async function remove() {
  try {
    await catalog.deleteCatalog(id(), entryId())
    await router.push({ name: 'catalog', params: { collectionId: id() } })
  } catch (cause) {
    error.value = message(cause)
    confirming.value = false
  }
}
</script>

<template>
  <section class="page-content workspace-content">
    <RouterLink class="back-link" :to="{ name: 'catalog', params: { collectionId: id() } }">← Catalog</RouterLink>
    <p v-if="catalog.loading">Loading…</p>
    <div v-else-if="catalog.entry">
      <div class="page-heading"><div><p class="eyebrow">Catalog entry</p><h1>{{ catalog.entry.display_title }}</h1></div></div>
      <p>Type: {{ catalog.entry.type }}</p>
      <p v-if="catalog.entry.sort_title">Sort title: {{ catalog.entry.sort_title }}</p>
      <p v-if="catalog.entry.notes">{{ catalog.entry.notes }}</p>
      <div v-if="canEdit">
        <button @click="beginEdit">Edit entry</button>
        <button class="button-danger" @click="confirming = true">Delete entry</button>
      </div>
      <form v-if="editing" class="collection-form panel" @submit.prevent="save">
        <label>Display title<input v-model="title" required /></label>
        <label>Type<input v-model="type" required /></label>
        <label>Sort title<input v-model="sortTitle" /></label>
        <label>Notes<textarea v-model="notes" /></label>
        <button>Save</button>
        <button type="button" @click="editing = false">Cancel</button>
      </form>
      <section v-if="confirming" class="confirmation panel">
        <p>Deleting this catalog entry also removes all editions, identifiers and physical inventory copies belonging to it.</p>
        <button class="button-danger" @click="remove">Confirm delete</button>
        <button @click="confirming = false">Cancel</button>
      </section>
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <h2>Editions</h2>
      <ul class="edition-list">
        <li v-for="edition in catalog.editions" :key="edition.id" class="edition-card panel">
          <h3>{{ edition.display_name }}</h3>
          <span v-if="edition.release_date"> · {{ edition.release_date }}</span>
          <span v-if="edition.publisher"> · {{ edition.publisher }}</span>
          <span v-if="edition.region"> · {{ edition.region }}</span>
          <span v-if="edition.language"> · {{ edition.language }}</span>
          <button v-if="canEdit" :aria-label="`Edit edition ${edition.display_name}`" @click="beginEditionEdit(edition)">Edit edition</button>
          <button v-if="canEdit" class="button-danger" :aria-label="`Delete edition ${edition.display_name}`" @click="confirmingEdition = edition.id">Delete edition</button>
          <section v-if="confirmingEdition === edition.id">
            <p>Deleting this edition also removes its identifiers and all physical inventory copies. The catalog entry remains.</p>
            <button class="button-danger" :disabled="deleteBusy" @click="confirmEditionDelete">{{ deleteBusy ? 'Deleting…' : 'Confirm delete' }}</button>
            <button @click="confirmingEdition = null">Cancel</button>
          </section>
          <form v-if="editingEdition === edition.id" @submit.prevent="saveEdition(edition.id)">
            <label>Display name<input v-model="editionForm.display_name" /></label>
            <label>Release date<input v-model="editionForm.release_date" type="date" /></label>
            <label>Publisher<input v-model="editionForm.publisher" /></label>
            <label>Region<input v-model="editionForm.region" /></label>
            <label>Language<input v-model="editionForm.language" /></label>
            <button>Save edition</button>
            <button type="button" @click="editingEdition = null">Cancel</button>
          </form>
          <section class="identifier-section">
            <h4>Barcodes &amp; IDs</h4>
            <ul>
              <li v-for="identifier in identifiers[edition.id] ?? []" :key="identifier.id">
                <span>{{ identifier.type }}: {{ identifier.value }}</span>
                <span v-if="identifier.source"> · {{ identifier.source }}</span>
                <button v-if="canEdit" :aria-label="`Edit identifier ${identifier.type} ${identifier.value}`" @click="beginIdentifierEdit(identifier)">Edit identifier</button>
                <button v-if="canEdit" class="button-danger" :aria-label="`Delete identifier ${identifier.type} ${identifier.value}`" @click="beginIdentifierDelete(identifier.id)">Delete identifier</button>
                <section v-if="confirmingIdentifier === identifier.id">
                  <p>Delete this identifier?</p>
                  <button class="button-danger" @click="confirmIdentifierDelete(edition.id, identifier.id)">Confirm delete identifier</button>
                  <button @click="confirmingIdentifier = null">Cancel</button>
                </section>
                <form v-if="editingIdentifier === identifier.id" @submit.prevent="saveIdentifier(edition.id, identifier.id)">
                  <label>Identifier type<input v-model="identifierForm.type" /></label>
                  <label>Identifier value<input v-model="identifierForm.value" /></label>
                  <label>Identifier source<input v-model="identifierForm.source" /></label>
                  <button>Save identifier</button>
                  <button type="button" @click="editingIdentifier = null">Cancel</button>
                </form>
              </li>
            </ul>
            <button v-if="canEdit && addingIdentifier !== edition.id" :aria-label="`Add identifier to ${edition.display_name}`" @click="beginIdentifierAdd(edition.id)">Add identifier</button>
            <form v-if="addingIdentifier === edition.id" @submit.prevent="createIdentifier(edition.id)">
              <label>Identifier type<input v-model="identifierForm.type" /></label>
              <label>Identifier value<input v-model="identifierForm.value" /></label>
              <label>Identifier source<input v-model="identifierForm.source" /></label>
              <button>Create identifier</button>
              <button type="button" @click="addingIdentifier = null">Cancel</button>
            </form>
          </section>
        </li>
      </ul>
      <form v-if="canEdit" class="collection-form panel" @submit.prevent="add">
        <label>Edition name<input v-model="name" required /></label>
        <button>Add edition</button>
      </form>
    </div>
  </section>
</template>
