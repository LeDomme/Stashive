<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ApiError } from "@/api/client";
import type { Identifier } from "@/api/catalog";
import type { LocationTreeNode } from "@/api/locations";
import { useCatalogStore } from "@/stores/catalog";
import { useCollectionsStore } from "@/stores/collections";
import { useLibraryStore } from "@/stores/library";
import { useLocationsStore } from "@/stores/locations";
import PresetCustomField from "@/components/PresetCustomField.vue";
import MultiPresetCustomField from "@/components/MultiPresetCustomField.vue";
import { CONDITION_PRESETS, EDITION_PRESETS, LANGUAGE_PRESETS, MEDIA_FORMAT_PRESETS, PUBLISHER_PRESETS, REGION_PRESETS_BY_MEDIA_FORMAT } from "@/constants/inventoryPresets";
import { IDENTIFIER_TYPE_PRESETS } from "@/constants/inventoryPresets";
import { detectIdentifierType } from "@/utils/identifier";

const route = useRoute();
const router = useRouter();
const collections = useCollectionsStore();
const catalog = useCatalogStore();
const library = useLibraryStore();
const locations = useLocationsStore();
const section = ref<"general" | "identifiers" | "danger">("general");
const error = ref("");
const busy = ref(false);
const ready = ref(false);
const confirmingDelete = ref(false);
const confirmingIdentifier = ref<number | null>(null);
const addingIdentifier = ref(false);
const identifierTypeExpanded = ref(false);
const form = ref({ display_name: "", media_format: "", release_date: "", publisher: "", regions: [] as string[], languages: [] as string[] });
const copy = ref({ condition: "", notes: "", location_id: "" });
const identifierForm = ref({ type: "", value: "", source: "" });
const collectionId = computed(() => Number(route.params.collectionId));
const entryId = computed(() => Number(route.params.catalogEntryId));
const editionId = computed(() => route.params.editionId ? Number(route.params.editionId) : null);
const isNew = computed(() => editionId.value === null);
const canEdit = computed(() => ["owner", "admin", "editor"].includes(collections.collection?.role ?? ""));
const isMovieCollection = computed(() => collections.collection?.type === "movies");
const regionPresets = computed(() => REGION_PRESETS_BY_MEDIA_FORMAT[form.value.media_format] ?? []);
const locationOptions = computed(() => flatten(locations.tree));
const title = computed(() => library.title?.catalog_entry ?? null);
const edition = computed(() => library.title?.editions.find((item) => item.id === editionId.value) ?? null);
const identifiers = computed(() => edition.value?.identifiers ?? []);

function detailRoute() { return { name: "inventory-title", params: { collectionId: collectionId.value, catalogEntryId: entryId.value } }; }
function flatten(nodes: LocationTreeNode[], prefix = ""): { id: number; path: string }[] {
  return nodes.flatMap((node) => {
    const path = prefix ? `${prefix} > ${node.name}` : node.name;
    return [{ id: node.id, path }, ...flatten(node.children, path)];
  });
}
function message(cause: unknown, identifier = false) {
  if (cause instanceof ApiError) {
    if (cause.status === 403) return "You do not have permission for this action.";
    if (cause.status === 404) return identifier ? "This barcode or ID is not available." : "This edition is not available.";
    if (cause.status === 409) return identifier ? "This barcode or ID already exists for this edition." : "This change conflicts with existing data.";
    if (cause.status === 422) return identifier ? "Check the barcode or ID details." : "Check the edition details.";
  }
  return "This action could not be completed. Please try again.";
}
function resetIdentifierForm() { identifierForm.value = { type: "", value: "", source: "" }; identifierTypeExpanded.value = false; }
function updateIdentifierValue(value: string) {
  identifierForm.value.value = value;
  if (!identifierTypeExpanded.value) identifierForm.value.type = detectIdentifierType(value.trim()) ?? "";
}
async function load() {
  error.value = "";
  ready.value = false;
  await collections.loadCollection(collectionId.value);
  if (!canEdit.value) return;
  await Promise.all([library.loadDetail(collectionId.value, entryId.value), locations.loadTree(collectionId.value)]);
  if (!isNew.value && !edition.value) { error.value = "This edition is not available."; return; }
  if (edition.value) form.value = { display_name: edition.value.display_name, media_format: edition.value.media_format ?? "", release_date: edition.value.release_date ?? "", publisher: edition.value.publisher ?? "", regions: edition.value.regions, languages: edition.value.languages };
  else form.value = { display_name: "", media_format: "", release_date: "", publisher: "", regions: [], languages: [] };
  ready.value = true;
}
async function refreshLibrary() {
  await Promise.all([library.loadDetail(collectionId.value, entryId.value), library.load(collectionId.value)]);
}
function editionPayload() {
  const generic = { display_name: form.value.display_name.trim(), release_date: form.value.release_date || null };
  if (!isMovieCollection.value) return generic;
  return { ...generic, media_format: form.value.media_format.trim() || null, publisher: form.value.publisher.trim() || null, regions: form.value.regions, languages: form.value.languages };
}
function addItemEditionPayload() {
  return {
    display_name: form.value.display_name.trim(),
    media_format: isMovieCollection.value ? form.value.media_format.trim() || null : null,
    release_date: form.value.release_date || null,
    publisher: isMovieCollection.value ? form.value.publisher.trim() || null : null,
    regions: isMovieCollection.value ? form.value.regions : [],
    languages: isMovieCollection.value ? form.value.languages : [],
  };
}
watch(() => form.value.media_format, (format, previous) => {
  if (!isNew.value || !previous || format === previous) return;
  const previousPresets = REGION_PRESETS_BY_MEDIA_FORMAT[previous] ?? [];
  const currentPresets = new Set(REGION_PRESETS_BY_MEDIA_FORMAT[format] ?? []);
  form.value.regions = form.value.regions.filter((region) => !previousPresets.includes(region) || currentPresets.has(region));
});
async function save() {
  if (!form.value.display_name.trim()) { error.value = "Edition name is required."; return; }
  busy.value = true;
  try {
    if (isNew.value) await library.addItem(collectionId.value, {
      title: { existing_id: entryId.value, new: null },
      edition: { existing_id: null, new: addItemEditionPayload() },
      copy: { condition: copy.value.condition || null, notes: copy.value.notes || null, location_id: Number(copy.value.location_id) || null },
    });
    else await catalog.updateEdition(collectionId.value, editionId.value!, editionPayload());
    await refreshLibrary();
    await router.push(detailRoute());
  } catch (cause) { error.value = message(cause); } finally { busy.value = false; }
}
async function addIdentifier() {
  if (!editionId.value || !identifierForm.value.type.trim() || !identifierForm.value.value.trim()) { error.value = "Type and value are required."; return; }
  busy.value = true;
  try {
    await catalog.createIdentifier(collectionId.value, editionId.value, { type: identifierForm.value.type.trim(), value: identifierForm.value.value.trim(), source: "manual" });
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
    <RouterLink class="back-link" :to="detailRoute()">Back to title</RouterLink>
    <p v-if="!canEdit && collections.collection" class="form-error" role="alert">You do not have permission to manage this edition.</p>
    <div v-else-if="title && (isNew || edition) && ready" class="management-layout inventory-management">
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
          <label>Release date <span class="optional">optional</span><input v-model="form.release_date" type="date" /></label>
          <section v-if="isMovieCollection" class="form-field-group">
            <p class="form-field-group__heading">Movie metadata</p>
            <PresetCustomField id="edition-format" v-model="form.media_format" label="Media format" :presets="MEDIA_FORMAT_PRESETS" allow-empty empty-value="" />
            <PresetCustomField id="publisher" v-model="form.publisher" label="Publisher / distributor" :presets="PUBLISHER_PRESETS" allow-empty empty-value="" />
            <template v-if="form.media_format">
              <MultiPresetCustomField id="regions" v-model="form.regions" label="Regions" :presets="regionPresets" />
            </template>
            <p v-else class="field-hint">Choose a media format to select regions.</p>
            <MultiPresetCustomField id="languages" v-model="form.languages" label="Languages" :presets="LANGUAGE_PRESETS" />
            <p v-if="!isNew && form.media_format !== edition?.media_format" class="field-hint">Review regions after changing media format.</p>
          </section>
          <section v-if="isNew" class="form-field-group">
            <p class="eyebrow">Physical copy</p>
            <PresetCustomField id="copy-condition" v-model="copy.condition" label="Condition" :presets="CONDITION_PRESETS" allow-empty empty-value="" />
            <label>Location <span class="optional">optional</span><select v-model="copy.location_id"><option value="">Unassigned</option><option v-for="location in locationOptions" :key="location.id" :value="String(location.id)">{{ location.path }}</option></select></label>
            <label>Notes <span class="optional">optional</span><textarea v-model="copy.notes" /></label>
          </section>
          <div class="action-row"><button :disabled="busy">{{ busy ? "Saving…" : isNew ? "Add edition & copy" : "Save edition" }}</button><RouterLink class="button-secondary button-link" :to="detailRoute()">Cancel</RouterLink></div>
        </form>
        <section v-else-if="section === 'identifiers'" class="identifier-management">
          <h1>Barcodes &amp; IDs</h1>
          <p v-if="!identifiers.length" class="state-message">No barcodes or IDs.</p>
          <ul v-else class="identifier-read-list identifier-rows">
            <li v-for="identifier in identifiers" :key="identifier.id"><strong class="identifier-type-badge">{{ identifier.type }}</strong><code>{{ identifier.value }}</code><small v-if="identifier.source && identifier.source.toLowerCase() !== 'manual'">{{ identifier.source }}</small><button class="button-danger button-compact" @click="confirmingIdentifier = identifier.id">Delete</button><div v-if="confirmingIdentifier === identifier.id" class="confirmation"><p>Delete this barcode or ID?</p><button class="button-danger button-compact" :disabled="busy" @click="removeIdentifier(identifier)">Confirm delete</button><button class="button-secondary button-compact" :disabled="busy" @click="confirmingIdentifier = null">Cancel</button></div></li>
          </ul>
          <button v-if="!addingIdentifier" @click="addingIdentifier = true">Add barcode or ID</button>
          <form v-else class="collection-form compact-form" @submit.prevent="addIdentifier">
            <label>Barcode / ID<input :value="identifierForm.value" autocomplete="off" @input="updateIdentifierValue(($event.target as HTMLInputElement).value)" required /></label>
            <p v-if="identifierForm.type && !identifierTypeExpanded" class="field-hint">Detected type: <strong>{{ identifierForm.type }}</strong> <button type="button" class="button-ghost button-compact" @click="identifierTypeExpanded = true">Change type</button></p>
            <template v-else><p v-if="!identifierForm.type" class="field-hint">Choose a type for this custom ID.</p><PresetCustomField id="identifier-type" v-model="identifierForm.type" label="Type" :presets="IDENTIFIER_TYPE_PRESETS" /></template>
            <div class="action-row"><button :disabled="busy">{{ busy ? "Adding…" : "Add barcode / ID" }}</button><button type="button" class="button-secondary" :disabled="busy" @click="addingIdentifier = false; resetIdentifierForm()">Cancel</button></div>
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
