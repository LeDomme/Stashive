<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ApiError } from "@/api/client";
import type { CatalogEntry, Edition } from "@/api/catalog";
import type { LocationTreeNode } from "@/api/locations";
import { useCatalogStore } from "@/stores/catalog";
import { useCollectionsStore } from "@/stores/collections";
import { useInventoryStore } from "@/stores/inventory";
import { useLibraryStore } from "@/stores/library";
import { useLocationsStore } from "@/stores/locations";

const route = useRoute();
const collections = useCollectionsStore();
const catalog = useCatalogStore();
const inventory = useInventoryStore();
const library = useLibraryStore();
const locations = useLocationsStore();
const editions = ref<(Edition & { title: string })[]>([]);
const adding = ref(false);
const error = ref("");
const form = ref({ edition_id: "", condition: "", notes: "" });
const filter = ref<"all" | "unassigned" | "location">("all");
const filterLocation = ref("");
const descendants = ref(true);
const id = computed(() => Number(route.params.collectionId));
const canEdit = computed(() => ["owner", "admin", "editor"].includes(collections.collection?.role ?? ""));
const totalCopies = computed(() => library.titles.reduce((total, title) => total + title.copy_count, 0));

function message(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 403) return "You do not have permission for this action.";
    if (error.status === 404) return "This inventory data is no longer available.";
    if (error.status === 422) return "Check the selected inventory filter or physical copy details.";
  }
  return "This action could not be completed. Please try again.";
}

function flatten(nodes: LocationTreeNode[], prefix = ""): { id: number; path: string }[] {
  return nodes.flatMap((node) => {
    const path = prefix ? `${prefix} > ${node.name}` : node.name;
    return [{ id: node.id, path }, ...flatten(node.children, path)];
  });
}

const locationOptions = computed(() => flatten(locations.tree));
function filterPayload() {
  if (filter.value === "unassigned") return { unassigned: true };
  if (filter.value === "location" && Number(filterLocation.value)) {
    return { locationId: Number(filterLocation.value), includeDescendants: descendants.value };
  }
  return {};
}
function resetForm() { form.value = { edition_id: "", condition: "", notes: "" }; }

async function load() {
  error.value = "";
  await collections.loadCollection(id.value);
  if (!collections.collection) return;
  await Promise.all([library.load(id.value, filterPayload()), catalog.load(id.value), locations.loadTree(id.value)]);
  if (library.error) error.value = message(library.error);
  try {
    const groups = await Promise.all(catalog.entries.map(async (entry: CatalogEntry) => ({
      entry, editions: await catalog.listEditions(id.value, entry.id),
    })));
    editions.value = groups.flatMap((group) => group.editions.map((edition) => ({ ...edition, title: group.entry.display_title })));
  } catch (cause) { error.value = message(cause); }
}
async function clearFilters() {
  filter.value = "all"; filterLocation.value = ""; descendants.value = true; await load();
}
function beginAdd() { error.value = ""; resetForm(); adding.value = true; }
async function create() {
  const editionId = Number(form.value.edition_id);
  if (!editionId) { error.value = "Choose an edition."; return; }
  try {
    await inventory.createInventoryItem(id.value, { edition_id: editionId, condition: form.value.condition.trim() || null, notes: form.value.notes.trim() || null });
    adding.value = false; resetForm(); await library.load(id.value, filterPayload());
    if (library.error) error.value = message(library.error);
  } catch (cause) { error.value = message(cause); }
}
watch(() => route.params.collectionId, load, { immediate: true });
</script>

<template>
  <section class="page-content workspace-content">
    <template v-if="collections.collection">
      <div class="page-heading">
        <div><p class="eyebrow">{{ collections.collection.name }}</p><h1>Inventory</h1></div>
        <button v-if="canEdit && library.titles.length" @click="beginAdd">Add item</button>
      </div>
      <nav class="collection-nav" aria-label="Collection navigation">
        <RouterLink :to="{ name: 'inventory', params: { collectionId: id } }">Inventory</RouterLink>
        <RouterLink :to="{ name: 'locations', params: { collectionId: id } }">Locations</RouterLink>
        <RouterLink :to="{ name: 'collection-settings', params: { collectionId: id } }">Settings</RouterLink>
      </nav>
      <section class="filter-toolbar panel">
        <form class="filter-toolbar__controls" @submit.prevent="load">
          <label class="toolbar-field"><span>Filter</span><select v-model="filter" @change="filter !== 'location' && (filterLocation = '')"><option value="all">All</option><option value="unassigned">Unassigned</option><option value="location">Location</option></select></label>
          <label v-if="filter === 'location'" class="toolbar-field"><span class="visually-hidden">Location</span><select v-model="filterLocation" aria-label="Location"><option value="">Choose a location</option><option v-for="option in locationOptions" :key="option.id" :value="String(option.id)">{{ option.path }}</option></select></label>
          <label v-if="filter === 'location'" class="checkbox-label toolbar-checkbox"><input v-model="descendants" type="checkbox" /><span>Include sublocations</span></label>
          <div class="filter-toolbar__actions"><button class="button-secondary button-compact">Apply filter</button><button v-if="filter !== 'all' || filterLocation || !descendants" type="button" class="button-ghost button-compact" @click="clearFilters">Clear</button></div>
        </form>
        <p class="filter-toolbar__summary">{{ library.titles.length }} {{ library.titles.length === 1 ? 'title' : 'titles' }} · {{ totalCopies }} physical {{ totalCopies === 1 ? 'copy' : 'copies' }}</p>
      </section>
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <form v-if="adding" class="collection-form panel modal-panel" @submit.prevent="create">
        <h2>Add item</h2>
        <label>Edition<select v-model="form.edition_id"><option value="" disabled>Choose an edition</option><option v-for="edition in editions" :key="edition.id" :value="String(edition.id)">{{ edition.title }} — {{ edition.display_name }}</option></select></label>
        <label>Condition <span class="optional">optional</span><input v-model="form.condition" /></label>
        <label>Notes <span class="optional">optional</span><textarea v-model="form.notes" /></label>
        <div class="action-row"><button>Create physical copy</button><button type="button" class="button-secondary" @click="adding = false; resetForm()">Cancel</button></div>
      </form>
      <div v-if="!library.titles.length" class="empty-state">
        <h2>{{ filter === 'all' ? 'No titles yet' : 'No titles match this filter' }}</h2>
        <p>{{ canEdit ? 'Add an item once an edition is available.' : 'This collection has no matching titles.' }}</p>
        <button v-if="canEdit" @click="beginAdd">Add item</button>
      </div>
      <ul v-else class="library-grid" aria-label="Inventory titles">
        <li v-for="title in library.titles" :key="title.catalog_entry_id" class="library-card">
          <RouterLink class="library-card__link" :to="{ name: 'inventory-title', params: { collectionId: id, catalogEntryId: title.catalog_entry_id } }" :aria-label="`Open ${title.display_title}`">
            <span class="library-card__cover" aria-hidden="true">Stashive</span>
            <span class="library-card__body"><span class="library-card__title">{{ title.display_title }}</span><span class="library-card__summary">{{ title.edition_count }} {{ title.edition_count === 1 ? 'edition' : 'editions' }} · {{ title.copy_count }} {{ title.copy_count === 1 ? 'copy' : 'copies' }}</span><span v-if="title.media_formats.length" class="library-card__formats">{{ title.media_formats.join(' · ') }}</span></span>
          </RouterLink>
        </li>
      </ul>
    </template>
  </section>
</template>
