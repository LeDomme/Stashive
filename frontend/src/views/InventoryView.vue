<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ApiError } from "@/api/client";
import type { CatalogEntry, Edition } from "@/api/catalog";
import type { InventoryItem } from "@/api/inventory";
import type { LocationTreeNode } from "@/api/locations";
import { useCatalogStore } from "@/stores/catalog";
import { useCollectionsStore } from "@/stores/collections";
import { useInventoryStore } from "@/stores/inventory";
import { useLocationsStore } from "@/stores/locations";
const route = useRoute(),
  collections = useCollectionsStore(),
  inventory = useInventoryStore(),
  catalog = useCatalogStore(),
  locations = useLocationsStore();
const editions = ref<(Edition & { title: string })[]>([]),
  adding = ref(false),
  editing = ref<number | null>(null),
  deleting = ref<number | null>(null),
  assigning = ref<number | null>(null),
  error = ref(""),
  form = ref({ edition_id: "", condition: "", notes: "" }),
  locationId = ref(""),
  filter = ref<"all" | "unassigned" | "location">("all"),
  filterLocation = ref(""),
  descendants = ref(true);
const id = computed(() => Number(route.params.collectionId)),
  canEdit = computed(() =>
    ["owner", "admin", "editor"].includes(collections.collection?.role ?? ""),
  );
function message(e: unknown) {
  if (e instanceof ApiError) {
    if (e.status === 403) return "You do not have permission for this action.";
    if (e.status === 404) return "This inventory item is no longer available.";
    if (e.status === 409) return "This change conflicts with existing data.";
    if (e.status === 422) return "Check the entered physical copy details.";
  }
  return "This action could not be completed. Please try again.";
}
function flatten(
  nodes: LocationTreeNode[],
  prefix = "",
): { id: number; path: string }[] {
  return nodes.flatMap((n) => {
    const path = prefix ? `${prefix} > ${n.name}` : n.name;
    return [{ id: n.id, path }, ...flatten(n.children, path)];
  });
}
const locationOptions = computed(() => flatten(locations.tree));
function path(item: InventoryItem) {
  return item.location_id === null
    ? "Unassigned"
    : (locationOptions.value.find((x) => x.id === item.location_id)?.path ??
        "Assigned");
}
function edition(item: InventoryItem) {
  return editions.value.find((x) => x.id === item.edition_id);
}
async function load() {
  error.value = "";
  await collections.loadCollection(id.value);
  if (!collections.collection) return;
  const f =
    filter.value === "unassigned"
      ? { unassigned: true }
      : filter.value === "location" && +filterLocation.value
        ? {
            locationId: +filterLocation.value,
            includeDescendants: descendants.value,
          }
        : {};
  await Promise.all([
    inventory.load(id.value, f),
    catalog.load(id.value),
    locations.loadTree(id.value),
  ]);
  try {
    const groups = await Promise.all(
      catalog.entries.map(async (entry: CatalogEntry) => ({
        entry,
        editions: await catalog.listEditions(id.value, entry.id),
      })),
    );
    editions.value = groups.flatMap((g) =>
      g.editions.map((e) => ({ ...e, title: g.entry.display_title })),
    );
  } catch (e) {
    error.value = message(e);
  }
}
watch(() => route.params.collectionId, load, { immediate: true });
function reset() {
  form.value = { edition_id: "", condition: "", notes: "" };
}
function beginAdd() {
  error.value = "";
  editing.value = null;
  deleting.value = null;
  reset();
  adding.value = true;
}
function beginEdit(item: InventoryItem) {
  editing.value = item.id;
  form.value = {
    edition_id: String(item.edition_id),
    condition: item.condition ?? "",
    notes: item.notes ?? "",
  };
  error.value = "";
}
function cancelEdit() {
  editing.value = null;
  reset();
}
function beginAssign(item: InventoryItem) {
  assigning.value = item.id;
  locationId.value = item.location_id === null ? "" : String(item.location_id);
  error.value = "";
}
async function clearFilters() {
  filter.value = "all";
  filterLocation.value = "";
  descendants.value = true;
  await load();
}
async function create() {
  const editionId = Number(form.value.edition_id);
  if (!editionId) {
    error.value = "Choose an edition.";
    return;
  }
  try {
    const item = await inventory.createInventoryItem(id.value, {
      edition_id: editionId,
      condition: form.value.condition.trim() || null,
      notes: form.value.notes.trim() || null,
    });
    inventory.items.push(item);
    adding.value = false;
    reset();
  } catch (e) {
    error.value = message(e);
  }
}
async function assign(itemId: number) {
  try {
    const item = await inventory.updateInventoryItem(id.value, itemId, {
      location_id: locationId.value ? +locationId.value : null,
    });
    const i = inventory.items.findIndex((x) => x.id === itemId);
    if (i >= 0) inventory.items.splice(i, 1, item);
    assigning.value = null;
  } catch (e) {
    error.value = message(e);
  }
}
async function save(itemId: number) {
  try {
    const item = await inventory.updateInventoryItem(id.value, itemId, {
      condition: form.value.condition.trim() || null,
      notes: form.value.notes.trim() || null,
    });
    const i = inventory.items.findIndex((x) => x.id === itemId);
    if (i >= 0) inventory.items.splice(i, 1, item);
    editing.value = null;
  } catch (e) {
    error.value = message(e);
  }
}
async function remove(itemId: number) {
  try {
    await inventory.deleteInventoryItem(id.value, itemId);
    inventory.items = inventory.items.filter((item) => item.id !== itemId);
    deleting.value = null;
  } catch (e) {
    error.value = message(e);
  }
}
</script>
<template>
  <section class="page-content workspace-content">
    <template v-if="collections.collection"
      ><div class="page-heading">
        <div>
          <p class="eyebrow">{{ collections.collection.name }}</p>
          <h1>Inventory</h1>
        </div>
        <button v-if="canEdit" @click="beginAdd">Add physical copy</button>
      </div>
      <nav class="collection-nav" aria-label="Collection navigation">
        <RouterLink :to="{ name: 'inventory', params: { collectionId: id } }"
          >Inventory</RouterLink
        ><RouterLink :to="{ name: 'catalog', params: { collectionId: id } }"
          >Catalog</RouterLink
        ><RouterLink :to="{ name: 'locations', params: { collectionId: id } }"
          >Locations</RouterLink
        ><RouterLink
          :to="{ name: 'collection-settings', params: { collectionId: id } }"
          >Settings</RouterLink
        >
      </nav>
      <section class="filter-toolbar panel">
      <form class="filter-toolbar__controls" @submit.prevent="load">
        <label class="toolbar-field"
          ><span>Filter</span><select
            v-model="filter"
            @change="filter !== 'location' && (filterLocation = '')"
          >
            <option value="all">All</option>
            <option value="unassigned">Unassigned</option>
            <option value="location">Location</option>
          </select></label
        ><label v-if="filter === 'location'" class="toolbar-field"
          ><span class="visually-hidden">Location</span><select v-model="filterLocation" aria-label="Location">
            <option value="">Choose a location</option>
            <option v-for="x in locationOptions" :value="String(x.id)">
              {{ x.path }}
            </option>
          </select></label
        ><label v-if="filter === 'location'" class="checkbox-label toolbar-checkbox"
          ><input type="checkbox" v-model="descendants" /> <span>Include
          sublocations</span></label
        ><div class="filter-toolbar__actions"><button class="button-secondary button-compact">Apply filter</button>
          <button v-if="filter !== 'all' || filterLocation || !descendants" type="button" class="button-ghost button-compact" @click="clearFilters">Clear</button>
        </div>
      </form>
      <p class="filter-toolbar__summary">{{ inventory.items.length }} physical {{ inventory.items.length === 1 ? 'copy' : 'copies' }}</p>
      </section>
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <form
        v-if="adding"
        class="collection-form panel modal-panel"
        @submit.prevent="create"
      >
        <h2>Add physical copy</h2>
        <label
          >Edition<select v-model="form.edition_id">
            <option value="" disabled>Choose an edition</option>
            <option v-for="edition in editions" :value="String(edition.id)">
              {{ edition.title }} — {{ edition.display_name }}
            </option>
          </select></label
        ><label
          >Condition <span class="optional">optional</span
          ><input v-model="form.condition" /></label
        ><label
          >Notes <span class="optional">optional</span
          ><textarea v-model="form.notes" />
        </label>
        <div class="action-row">
          <button>Create physical copy</button
          ><button
            type="button"
            class="button-secondary"
            @click="
              adding = false;
              reset();
            "
          >
            Cancel
          </button>
        </div>
      </form>
      <div v-if="!inventory.items.length" class="empty-state">
        <h2>No physical copies yet</h2>
        <p>Add a copy once a catalog edition is available.</p>
      </div>
      <ul v-else class="inventory-list">
        <li
          v-for="item in inventory.items"
          :key="item.id"
          class="inventory-card"
        >
          <div class="inventory-card__body">
            <p class="inventory-card__eyebrow">Physical copy</p>
            <h2>{{ edition(item)?.title }}</h2>
            <p class="inventory-card__edition">
              {{ edition(item)?.display_name }}
            </p>
            <dl class="inventory-card__metadata">
              <div>
                <dt>Location</dt>
                <dd>{{ path(item) }}</dd>
              </div>
              <div v-if="item.condition">
                <dt>Condition</dt>
                <dd>{{ item.condition }}</dd>
              </div>
              <div v-if="item.notes">
                <dt>Notes</dt>
                <dd>{{ item.notes }}</dd>
              </div>
            </dl>
          </div>
          <div v-if="canEdit" class="action-row inventory-card__actions">
            <button
              class="button-secondary button-compact"
              @click="beginAssign(item)"
            >
              {{
                item.location_id === null
                  ? "Assign location"
                  : "Change location"
              }}</button
            ><button
              v-if="item.location_id !== null"
              class="button-secondary button-compact"
              @click="
                beginAssign(item);
                locationId = '';
              "
            >
              Remove location</button
            ><button
              class="button-secondary button-compact"
              @click="beginEdit(item)"
            >
              Edit copy</button
            ><button type="button" class="button-danger button-icon" aria-label="Delete copy" title="Delete copy" @click="deleting = item.id">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 7h14M10 11v6m4-6v6M9 7l1-2h4l1 2m-8 0 1 13h8l1-13" /></svg>
            </button>
          </div>
          <form
            v-if="assigning === item.id"
            class="inline-form"
            @submit.prevent="assign(item.id)"
          >
            <label
              >Location<select v-model="locationId">
                <option value="">Unassigned</option>
                <option v-for="x in locationOptions" :value="String(x.id)">
                  {{ x.path }}
                </option>
              </select></label
            ><button>Save location</button>
          </form>
          <form
            v-if="editing === item.id"
            class="inline-form"
            @submit.prevent="save(item.id)"
          >
            <h3>Edit physical copy</h3>
            <label>Condition<input v-model="form.condition" /></label
            ><label>Notes<textarea v-model="form.notes" /></label>
            <div class="action-row">
              <button>Save copy</button
              ><button
                type="button"
                class="button-secondary"
                @click="cancelEdit"
              >
                Cancel
              </button>
            </div>
          </form>
          <section v-if="deleting === item.id" class="confirmation">
            <p>
              Delete this physical copy? This deletes only this copy; its
              catalog entry, edition, identifiers, and other copies remain.
            </p>
            <div class="action-row">
              <button class="button-danger" @click="remove(item.id)">
                Confirm delete copy</button
              ><button class="button-secondary" @click="deleting = null">
                Cancel
              </button>
            </div>
          </section>
        </li>
      </ul></template
    >
  </section>
</template>
