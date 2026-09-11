<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ApiError } from "@/api/client";
import type { InventoryItem } from "@/api/inventory";
import type { LocationTreeNode } from "@/api/locations";
import { useCollectionsStore } from "@/stores/collections";
import { useInventoryStore } from "@/stores/inventory";
import { useLibraryStore } from "@/stores/library";
import { useLocationsStore } from "@/stores/locations";
import PresetCustomField from "@/components/PresetCustomField.vue";
import { CONDITION_PRESETS } from "@/constants/inventoryPresets";

const route = useRoute();
const router = useRouter();
const collections = useCollectionsStore();
const inventory = useInventoryStore();
const library = useLibraryStore();
const locations = useLocationsStore();
const section = ref<"general" | "location" | "danger">("general");
const error = ref("");
const busy = ref(false);
const confirmingDelete = ref(false);
const ready = ref(false);
const form = ref({ condition: "", notes: "" });
const selectedLocation = ref("");
const collectionId = computed(() => Number(route.params.collectionId));
const entryId = computed(() => Number(route.params.catalogEntryId));
const editionId = computed(() => Number(route.params.editionId));
const itemId = computed(() => Number(route.params.inventoryItemId));
const canEdit = computed(() => ["owner", "admin", "editor"].includes(collections.collection?.role ?? ""));
const edition = computed(() => library.title?.editions.find((candidate) => candidate.id === editionId.value) ?? null);
const copy = computed(() => edition.value?.copies.find((candidate) => candidate.id === itemId.value) ?? null);

function flatten(nodes: LocationTreeNode[], prefix = ""): { id: number; path: string }[] {
  return nodes.flatMap((node) => {
    const path = prefix ? `${prefix} > ${node.name}` : node.name;
    return [{ id: node.id, path }, ...flatten(node.children, path)];
  });
}
const locationOptions = computed(() => flatten(locations.tree));
function pathFor(item: InventoryItem) {
  if (item.location_id === null) return "Unassigned";
  return locationOptions.value.find((location) => location.id === item.location_id)?.path ?? "Assigned";
}
function sortedCopies(copies: InventoryItem[]) {
  return [...copies].sort((first, second) => first.created_at.localeCompare(second.created_at) || first.id - second.id);
}
const copyNumber = computed(() => {
  if (!edition.value || !copy.value) return null;
  return sortedCopies(edition.value.copies).findIndex((candidate) => candidate.id === copy.value?.id) + 1;
});
function detailRoute() { return { name: "inventory-title", params: { collectionId: collectionId.value, catalogEntryId: entryId.value } }; }
function message(cause: unknown) {
  if (cause instanceof ApiError) {
    if (cause.status === 403) return "You do not have permission for this action.";
    if (cause.status === 404) return "This physical copy is not available.";
    if (cause.status === 422) return "Check the physical copy details.";
  }
  return "This action could not be completed. Please try again.";
}
async function refreshLibrary() {
  await Promise.all([library.loadDetail(collectionId.value, entryId.value), library.load(collectionId.value)]);
}
async function load() {
  error.value = "";
  ready.value = false;
  await collections.loadCollection(collectionId.value);
  if (!canEdit.value) return;
  await Promise.all([library.loadDetail(collectionId.value, entryId.value), locations.loadTree(collectionId.value)]);
  if (!edition.value || !copy.value) { error.value = "This physical copy is not available."; return; }
  form.value = { condition: copy.value.condition ?? "", notes: copy.value.notes ?? "" };
  selectedLocation.value = copy.value.location_id === null ? "" : String(copy.value.location_id);
  ready.value = true;
}
async function saveGeneral() {
  if (!copy.value) return;
  busy.value = true;
  try {
    await inventory.updateInventoryItem(collectionId.value, copy.value.id, { condition: form.value.condition.trim() || null, notes: form.value.notes.trim() || null });
    await refreshLibrary(); await router.push(detailRoute());
  } catch (cause) { error.value = message(cause); } finally { busy.value = false; }
}
async function saveLocation(locationId: number | null) {
  if (!copy.value) return;
  busy.value = true;
  try {
    await inventory.updateInventoryItem(collectionId.value, copy.value.id, { location_id: locationId });
    await refreshLibrary();
    const updated = library.title?.editions.find((candidate) => candidate.id === editionId.value)?.copies.find((candidate) => candidate.id === itemId.value);
    selectedLocation.value = updated?.location_id === null || updated === undefined ? "" : String(updated.location_id);
  } catch (cause) { error.value = message(cause); } finally { busy.value = false; }
}
async function remove() {
  if (!copy.value) return;
  busy.value = true;
  try {
    await inventory.deleteInventoryItem(collectionId.value, copy.value.id);
    await refreshLibrary(); await router.push(detailRoute());
  } catch (cause) { error.value = message(cause); confirmingDelete.value = false; } finally { busy.value = false; }
}
watch(() => [route.params.collectionId, route.params.catalogEntryId, route.params.editionId, route.params.inventoryItemId], load, { immediate: true });
</script>

<template>
  <section class="page-content workspace-content">
    <RouterLink class="back-link" :to="detailRoute()">← Back to title</RouterLink>
    <p v-if="!canEdit && collections.collection" class="form-error" role="alert">You do not have permission to manage this physical copy.</p>
    <div v-else-if="edition && copy && ready" class="management-layout inventory-management">
      <nav class="management-sidebar panel" aria-label="Physical copy management sections">
        <h2>Manage copy</h2>
        <button class="button-ghost" :class="{ 'is-active': section === 'general' }" @click="section = 'general'">General</button>
        <button class="button-ghost" :class="{ 'is-active': section === 'location' }" @click="section = 'location'">Location</button>
        <button class="button-ghost danger-link" :class="{ 'is-active': section === 'danger' }" @click="section = 'danger'">Danger zone</button>
      </nav>
      <section class="management-panel panel">
        <header class="copy-management-context"><p>{{ library.title?.catalog_entry.display_title }}</p><p>{{ edition.display_name }}<span v-if="edition.media_format"> · {{ edition.media_format }}</span></p><h1>Copy {{ copyNumber }}</h1></header>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <form v-if="section === 'general'" class="collection-form" @submit.prevent="saveGeneral">
          <PresetCustomField id="copy-condition" v-model="form.condition" label="Condition" :presets="CONDITION_PRESETS" allow-empty empty-value="" />
          <label>Notes <span class="optional">optional</span><textarea v-model="form.notes" /></label>
          <div class="action-row"><button :disabled="busy">{{ busy ? "Saving…" : "Save copy" }}</button><RouterLink class="button-secondary button-link" :to="detailRoute()">Cancel</RouterLink></div>
        </form>
        <section v-else-if="section === 'location'" class="copy-location-management">
          <h2>Location</h2>
          <p class="copy-location-management__current"><strong>Current location</strong><br />{{ pathFor(copy) }}</p>
          <form class="collection-form" @submit.prevent="saveLocation(selectedLocation ? Number(selectedLocation) : null)">
            <label>Move / Assign location<select v-model="selectedLocation"><option value="">Unassigned</option><option v-for="location in locationOptions" :key="location.id" :value="String(location.id)">{{ location.path }}</option></select></label>
            <div class="action-row"><button :disabled="busy">{{ busy ? "Saving…" : copy.location_id === null ? "Assign location" : "Move copy" }}</button><button v-if="copy.location_id !== null" type="button" class="button-secondary" :disabled="busy" @click="saveLocation(null)">Remove from location</button></div>
          </form>
        </section>
        <section v-else class="danger-zone">
          <h2>Danger zone</h2><p>Deleting this physical copy removes only this owned copy. The title and edition remain in your library.</p>
          <button v-if="!confirmingDelete" class="button-danger" @click="confirmingDelete = true">Delete physical copy</button>
          <div v-else class="confirmation"><p>Delete this physical copy?</p><div class="action-row"><button class="button-danger" :disabled="busy" @click="remove">{{ busy ? "Deleting…" : "Confirm delete physical copy" }}</button><button class="button-secondary" :disabled="busy" @click="confirmingDelete = false">Cancel</button></div></div>
        </section>
      </section>
    </div>
    <p v-else-if="error" class="form-error" role="alert">{{ error }}</p>
  </section>
</template>
