<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ApiError } from "@/api/client";
import type { Identifier } from "@/api/catalog";
import { useCatalogStore } from "@/stores/catalog";
import { useCollectionsStore } from "@/stores/collections";
import { useLibraryStore } from "@/stores/library";
import PresetCustomField from "@/components/PresetCustomField.vue";
import { EDITION_PRESETS, MEDIA_FORMAT_PRESETS } from "@/constants/inventoryPresets";

const route = useRoute();
const router = useRouter();
const collections = useCollectionsStore();
const catalog = useCatalogStore();
const library = useLibraryStore();
const section = ref<"general" | "identifiers" | "danger">("general");
const error = ref("");
const busy = ref(false);
const confirmingDelete = ref(false);
const confirmingIdentifier = ref<number | null>(null);
const addingIdentifier = ref(false);
const form = ref({ display_name: "", media_format: "", release_date: "", publisher: "", region: "", language: "" });
const identifierForm = ref({ type: "", value: "", source: "" });
const collectionId = computed(() => Number(route.params.collectionId));
const entryId = computed(() => Number(route.params.catalogEntryId));
const editionId = computed(() => route.params.editionId ? Number(route.params.editionId) : null);
const isNew = computed(() => editionId.value === null);
const canEdit = computed(() => ["owner", "admin", "editor"].includes(collections.collection?.role ?? ""));
const title = computed(() => library.title?.catalog_entry ?? null);
const edition = computed(() => library.title?.editions.find((item) => item.id === editionId.value) ?? null);
const identifiers = computed(() => edition.value?.identifiers ?? []);

function detailRoute() { return { name: "inventory-title", params: { collectionId: collectionId.value, catalogEntryId: entryId.value } }; }
function message(cause: unknown, identifier = false) {
  if (cause instanceof ApiError) {
    if (cause.status === 403) return "You do not have permission for this action.";
    if (cause.status === 404) return identifier ? "This barcode or ID is not available." : "This edition is not available.";
    if (cause.status === 409) return identifier ? "This barcode or ID already exists for this edition." : "This change conflicts with existing data.";
    if (cause.status === 422) return identifier ? "Check the barcode or ID details." : "Check the edition details.";
  }
  return "This action could not be completed. Please try again.";
}
function resetIdentifierForm() { identifierForm.value = { type: "", value: "", source: "" }; }
async function load() {
  error.value = "";
  await collections.loadCollection(collectionId.value);
  if (!canEdit.value) return;
  await library.loadDetail(collectionId.value, entryId.value);
  if (!isNew.value && !edition.value) { error.value = "This edition is not available."; return; }
  if (edition.value) form.value = { display_name: edition.value.display_name, media_format: edition.value.media_format ?? "", release_date: edition.value.release_date ?? "", publisher: edition.value.publisher ?? "", region: edition.value.region ?? "", language: edition.value.language ?? "" };
  else form.value = { display_name: "", media_format: "", release_date: "", publisher: "", region: "", language: "" };
}
async function refreshLibrary() {
  await Promise.all([library.loadDetail(collectionId.value, entryId.value), library.load(collectionId.value)]);
}
function editionPayload() {
  return { display_name: form.value.display_name.trim(), media_format: form.value.media_format.trim() || null, release_date: form.value.release_date || null, publisher: form.value.publisher.trim() || null, region: form.value.region.trim() || null, language: form.value.language.trim() || null };
}
async function save() {
  if (!form.value.display_name.trim()) { error.value = "Edition name is required."; return; }
  busy.value = true;
  try {
    if (isNew.value) await catalog.createEdition(collectionId.value, entryId.value, editionPayload());
    else await catalog.updateEdition(collectionId.value, editionId.value!, editionPayload());
    await refreshLibrary();
    await router.push(detailRoute());
  } catch (cause) { error.value = message(cause); } finally { busy.value = false; }
}
async function addIdentifier() {
  if (!editionId.value || !identifierForm.value.type.trim() || !identifierForm.value.value.trim()) { error.value = "Type and value are required."; return; }
  busy.value = true;
  try {
    await catalog.createIdentifier(collectionId.value, editionId.value, { type: identifierForm.value.type.trim(), value: identifierForm.value.value.trim(), source: identifierForm.value.source.trim() || null });
    resetIdentifierForm(); addingIdentifier.value = false; await refreshLibrary();
  } catch (cause) { error.value = message(cause, true); } finally { busy.value = false; }
}
async function removeIdentifier(identifier: Identifier) {
  if (!editionId.value) return;
  busy.value = true;
  try {
    await catalog.deleteIdentifier(collectionId.value, editionId.value, identifier.id);
    confirmingIdentifier.value = null; await refreshLibrary();
  } catch (cause) { error.value = message(cause, true); } finally { busy.value = false; }
}
async function removeEdition() {
  if (!editionId.value) return;
  busy.value = true;
  try {
    await catalog.deleteEdition(collectionId.value, editionId.value);
    await refreshLibrary(); await router.push(detailRoute());
  } catch (cause) { error.value = message(cause); confirmingDelete.value = false; } finally { busy.value = false; }
}
watch(() => [route.params.collectionId, route.params.catalogEntryId, route.params.editionId], load, { immediate: true });
</script>

<template>
  <section class="page-content workspace-content">
    <RouterLink class="back-link" :to="detailRoute()">← Back to title</RouterLink>
    <p v-if="!canEdit && collections.collection" class="form-error" role="alert">You do not have permission to manage this edition.</p>
    <div v-else-if="title && (isNew || edition)" class="management-layout inventory-management">
      <nav class="management-sidebar panel" aria-label="Edition management sections">
        <h2>{{ isNew ? "New edition" : "Manage edition" }}</h2>
        <button class="button-ghost" :class="{ 'is-active': section === 'general' }" @click="section = 'general'">General</button>
        <button v-if="!isNew" class="button-ghost" :class="{ 'is-active': section === 'identifiers' }" @click="section = 'identifiers'">Barcodes &amp; IDs</button>
        <button v-if="!isNew" class="button-ghost danger-link" :class="{ 'is-active': section === 'danger' }" @click="section = 'danger'">Danger zone</button>
      </nav>
      <section class="management-panel panel">
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <form v-if="section === 'general'" class="collection-form" @submit.prevent="save">
          <h1>{{ isNew ? "Add edition" : "Edition general" }}</h1>
          <PresetCustomField id="edition-name" v-model="form.display_name" label="Edition" :presets="EDITION_PRESETS" allow-empty empty-value="" />
          <PresetCustomField id="edition-format" v-model="form.media_format" label="Media format" :presets="MEDIA_FORMAT_PRESETS" allow-empty empty-value="" />
          <label>Release date <span class="optional">optional</span><input v-model="form.release_date" type="date" /></label>
          <label>Publisher <span class="optional">optional</span><input v-model="form.publisher" /></label>
          <label>Region <span class="optional">optional</span><input v-model="form.region" /></label>
          <label>Language <span class="optional">optional</span><input v-model="form.language" /></label>
          <div class="action-row"><button :disabled="busy">{{ busy ? "Saving…" : isNew ? "Create edition" : "Save edition" }}</button><RouterLink class="button-secondary button-link" :to="detailRoute()">Cancel</RouterLink></div>
        </form>
        <section v-else-if="section === 'identifiers'" class="identifier-management">
          <h1>Barcodes &amp; IDs</h1>
          <p v-if="!identifiers.length" class="state-message">No barcodes or IDs.</p>
          <ul v-else class="identifier-read-list">
            <li v-for="identifier in identifiers" :key="identifier.id"><strong>{{ identifier.type }}</strong><span>{{ identifier.value }}</span><small v-if="identifier.source">{{ identifier.source }}</small><button class="button-danger button-compact" @click="confirmingIdentifier = identifier.id">Delete</button><div v-if="confirmingIdentifier === identifier.id" class="confirmation"><p>Delete this barcode or ID?</p><button class="button-danger button-compact" :disabled="busy" @click="removeIdentifier(identifier)">Confirm delete</button><button class="button-secondary button-compact" :disabled="busy" @click="confirmingIdentifier = null">Cancel</button></div></li>
          </ul>
          <button v-if="!addingIdentifier" @click="addingIdentifier = true">Add barcode or ID</button>
          <form v-else class="collection-form compact-form" @submit.prevent="addIdentifier">
            <label>Type<input v-model="identifierForm.type" required /></label><label>Value<input v-model="identifierForm.value" required /></label><label>Source <span class="optional">optional</span><input v-model="identifierForm.source" /></label>
            <div class="action-row"><button :disabled="busy">{{ busy ? "Saving…" : "Save barcode or ID" }}</button><button type="button" class="button-secondary" :disabled="busy" @click="addingIdentifier = false; resetIdentifierForm()">Cancel</button></div>
          </form>
        </section>
        <section v-else class="danger-zone">
          <h1>Danger zone</h1><p>Deleting this edition also removes its barcodes and physical copies.</p>
          <button v-if="!confirmingDelete" class="button-danger" @click="confirmingDelete = true">Delete edition</button>
          <div v-else class="confirmation"><p>Delete this edition and its dependent inventory data?</p><div class="action-row"><button class="button-danger" :disabled="busy" @click="removeEdition">{{ busy ? "Deleting…" : "Confirm delete edition" }}</button><button class="button-secondary" :disabled="busy" @click="confirmingDelete = false">Cancel</button></div></div>
        </section>
      </section>
    </div>
    <p v-else-if="error" class="form-error" role="alert">{{ error }}</p>
  </section>
</template>
