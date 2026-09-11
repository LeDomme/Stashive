<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ApiError } from "@/api/client";
import { useCatalogStore } from "@/stores/catalog";
import { useCollectionsStore } from "@/stores/collections";
import { useLibraryStore } from "@/stores/library";

const route = useRoute();
const router = useRouter();
const collections = useCollectionsStore();
const catalog = useCatalogStore();
const library = useLibraryStore();
const section = ref<"general" | "danger">("general");
const error = ref("");
const busy = ref(false);
const confirmingDelete = ref(false);
const form = ref({ display_title: "", sort_title: "", type: "", notes: "" });
const collectionId = computed(() => Number(route.params.collectionId));
const entryId = computed(() => Number(route.params.catalogEntryId));
const canEdit = computed(() => ["owner", "admin", "editor"].includes(collections.collection?.role ?? ""));

function detailRoute() { return { name: "inventory-title", params: { collectionId: collectionId.value, catalogEntryId: entryId.value } }; }
function message(cause: unknown) {
  if (cause instanceof ApiError) {
    if (cause.status === 403) return "You do not have permission for this action.";
    if (cause.status === 404) return "This title is not available.";
    if (cause.status === 422) return "Check the title details.";
  }
  return "This action could not be completed. Please try again.";
}
async function load() {
  error.value = "";
  await collections.loadCollection(collectionId.value);
  if (!canEdit.value) return;
  await catalog.loadDetail(collectionId.value, entryId.value);
  if (!catalog.entry) return;
  form.value = { display_title: catalog.entry.display_title, sort_title: catalog.entry.sort_title ?? "", type: catalog.entry.type, notes: catalog.entry.notes ?? "" };
}
async function refreshLibrary() {
  await Promise.all([library.loadDetail(collectionId.value, entryId.value), library.load(collectionId.value)]);
}
async function save() {
  if (!form.value.display_title.trim() || !form.value.type.trim()) { error.value = "Display title and type are required."; return; }
  busy.value = true;
  try {
    await catalog.updateCatalog(collectionId.value, entryId.value, { display_title: form.value.display_title.trim(), sort_title: form.value.sort_title.trim() || null, type: form.value.type.trim(), notes: form.value.notes.trim() || null });
    await refreshLibrary();
    await router.push(detailRoute());
  } catch (cause) { error.value = message(cause); } finally { busy.value = false; }
}
async function remove() {
  busy.value = true;
  try {
    await catalog.deleteCatalog(collectionId.value, entryId.value);
    await library.load(collectionId.value);
    await router.push({ name: "inventory", params: { collectionId: collectionId.value } });
  } catch (cause) { error.value = message(cause); confirmingDelete.value = false; } finally { busy.value = false; }
}
watch(() => [route.params.collectionId, route.params.catalogEntryId], load, { immediate: true });
</script>

<template>
  <section class="page-content workspace-content">
    <RouterLink class="back-link" :to="detailRoute()">← Back to title</RouterLink>
    <p v-if="!canEdit && collections.collection" class="form-error" role="alert">You do not have permission to manage this title.</p>
    <div v-else-if="catalog.entry" class="management-layout inventory-management">
      <nav class="management-sidebar panel" aria-label="Title management sections">
        <h2>Manage title</h2>
        <button class="button-ghost" :class="{ 'is-active': section === 'general' }" @click="section = 'general'">General</button>
        <button class="button-ghost danger-link" :class="{ 'is-active': section === 'danger' }" @click="section = 'danger'">Danger zone</button>
      </nav>
      <section class="management-panel panel">
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <form v-if="section === 'general'" class="collection-form" @submit.prevent="save">
          <h1>Title general</h1>
          <label>Display title<input v-model="form.display_title" required /></label>
          <label>Sort title <span class="optional">optional</span><input v-model="form.sort_title" /></label>
          <label>Type<input v-model="form.type" required /></label>
          <label>Notes <span class="optional">optional</span><textarea v-model="form.notes" /></label>
          <div class="action-row"><button :disabled="busy">{{ busy ? "Saving…" : "Save title" }}</button><RouterLink class="button-secondary button-link" :to="detailRoute()">Cancel</RouterLink></div>
        </form>
        <section v-else class="danger-zone">
          <h1>Danger zone</h1>
          <p>Deleting this title also removes its editions, barcodes, and physical copies.</p>
          <button v-if="!confirmingDelete" class="button-danger" @click="confirmingDelete = true">Delete title</button>
          <div v-else class="confirmation"><p>Delete this title and its dependent inventory data?</p><div class="action-row"><button class="button-danger" :disabled="busy" @click="remove">{{ busy ? "Deleting…" : "Confirm delete title" }}</button><button class="button-secondary" :disabled="busy" @click="confirmingDelete = false">Cancel</button></div></div>
        </section>
      </section>
    </div>
  </section>
</template>
