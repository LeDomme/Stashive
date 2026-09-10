<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";

import LocationTreeNode from "@/components/LocationTreeNode.vue";
import { ApiError } from "@/api/client";
import type {
  LocationTreeNode as LocationNode,
  LocationType,
} from "@/api/locations";
import { useCollectionsStore } from "@/stores/collections";
import { useLocationsStore } from "@/stores/locations";

const route = useRoute();
const collections = useCollectionsStore();
const locations = useLocationsStore();
const editing = ref<LocationNode | null>(null);
const childParent = ref<LocationNode | null>(null);
const creatingRoot = ref(false);
const deleting = ref<LocationNode | null>(null);
const selected = ref<LocationNode | null>(null);
const busy = ref(false);
const actionError = ref("");
const name = ref("");
const type = ref<LocationType>("room");
const description = ref("");
const parentId = ref<number | null>(null);
const locationTypes: LocationType[] = [
  "room",
  "cabinet",
  "shelf",
  "box",
  "drawer",
  "other",
];
const typeLabels: Record<LocationType, string> = {
  room: "Room",
  cabinet: "Cabinet",
  shelf: "Shelf",
  box: "Box",
  drawer: "Drawer",
  other: "Other",
};
const collectionId = computed(() => Number(route.params.collectionId));
const canEdit = computed(() =>
  ["owner", "admin", "editor"].includes(collections.collection?.role ?? ""),
);

interface ParentOption {
  id: number;
  path: string;
}
function flatten(nodes: LocationNode[], prefix = ""): ParentOption[] {
  return nodes.flatMap((node) => {
    const path = prefix ? `${prefix} / ${node.name}` : node.name;
    return [{ id: node.id, path }, ...flatten(node.children, path)];
  });
}
function descendantIds(node: LocationNode): Set<number> {
  return new Set([
    node.id,
    ...node.children.flatMap((child) => [...descendantIds(child)]),
  ]);
}
const parentOptions = computed(() => {
  const excluded = editing.value
    ? descendantIds(editing.value)
    : new Set<number>();
  return flatten(locations.tree).filter((option) => !excluded.has(option.id));
});

function resetForm(): void {
  name.value = "";
  type.value = "room";
  description.value = "";
  parentId.value = null;
}
function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError))
    return "This action could not be completed. Please try again.";
  if (error.status === 409)
    return "This location still contains child locations or the move would create a cycle.";
  if (error.status === 403)
    return "You no longer have permission for this action.";
  if (error.status === 404)
    return "The collection or location is no longer available to you.";
  if (error.status === 422)
    return "Enter a valid name, type, and parent location.";
  return "This action could not be completed. Please try again.";
}
async function load(): Promise<void> {
  editing.value = null;
  childParent.value = null;
  creatingRoot.value = false;
  deleting.value = null;
  selected.value = null;
  actionError.value = "";
  await collections.loadCollection(collectionId.value);
  if (collections.collection) {
    await locations.loadTree(collectionId.value);
    selected.value = locations.tree[0] ?? null;
  }
}
function startRoot(): void {
  resetForm();
  creatingRoot.value = true;
  childParent.value = null;
  editing.value = null;
  actionError.value = "";
}
function startChild(node: LocationNode): void {
  resetForm();
  selected.value = node;
  creatingRoot.value = false;
  childParent.value = node;
  editing.value = null;
  actionError.value = "";
}
function startEdit(node: LocationNode): void {
  selected.value = node;
  creatingRoot.value = false;
  editing.value = node;
  childParent.value = null;
  name.value = node.name;
  type.value = node.type;
  description.value = node.description ?? "";
  parentId.value = node.parent_id;
  actionError.value = "";
}
function selectNode(node: LocationNode): void {
  selected.value = node;
  creatingRoot.value = false;
  childParent.value = null;
  editing.value = null;
  deleting.value = null;
  actionError.value = "";
}
async function saveCreate(): Promise<void> {
  if (!name.value.trim()) {
    actionError.value = "Enter a location name.";
    return;
  }
  busy.value = true;
  actionError.value = "";
  try {
    await locations.create(collectionId.value, {
      name: name.value.trim(),
      type: type.value,
      description: description.value.trim() || null,
      parent_id: childParent.value?.id ?? null,
    });
    resetForm();
    creatingRoot.value = false;
    childParent.value = null;
  } catch (error) {
    actionError.value = errorMessage(error);
  } finally {
    busy.value = false;
  }
}
async function saveEdit(): Promise<void> {
  if (!editing.value || !name.value.trim()) {
    actionError.value = "Enter a location name.";
    return;
  }
  busy.value = true;
  actionError.value = "";
  try {
    await locations.update(collectionId.value, editing.value.id, {
      name: name.value.trim(),
      type: type.value,
      description: description.value.trim() || null,
      parent_id: parentId.value ?? null,
    });
    editing.value = null;
  } catch (error) {
    actionError.value = errorMessage(error);
  } finally {
    busy.value = false;
  }
}
async function confirmDelete(): Promise<void> {
  if (!deleting.value) return;
  busy.value = true;
  actionError.value = "";
  try {
    await locations.remove(collectionId.value, deleting.value.id);
    deleting.value = null;
    selected.value = null;
  } catch (error) {
    actionError.value = errorMessage(error);
  } finally {
    busy.value = false;
  }
}
watch(() => route.params.collectionId, load, { immediate: true });
</script>

<template>
  <section
    class="page-content workspace-content"
    aria-labelledby="locations-heading"
  >
    <p
      v-if="collections.detailLoading || locations.loading"
      class="state-message"
      role="status"
    >
      Loading locations…
    </p>
    <div
      v-else-if="collections.detailError || locations.error"
      class="empty-state state-error"
      role="alert"
    >
      <h1>Locations unavailable</h1>
      <p
        v-if="
          collections.detailError?.status === 404 ||
          locations.error?.status === 404
        "
      >
        This collection is no longer available to you.
      </p>
      <p v-else>We could not load locations. Please try again.</p>
    </div>
    <template v-else-if="collections.collection">
      <div class="page-heading">
        <div>
          <p class="eyebrow">{{ collections.collection.name }}</p>
          <h1 id="locations-heading">Locations</h1>
        </div>
        <button v-if="canEdit" type="button" @click="startRoot">
          Add root location
        </button>
      </div>
      <nav class="collection-nav" aria-label="Collection navigation">
        <RouterLink :to="`/collections/${collectionId}/inventory`"
          >Inventory</RouterLink
        ><RouterLink :to="`/collections/${collectionId}/catalog`"
          >Catalog</RouterLink
        ><RouterLink :to="`/collections/${collectionId}/locations`"
          >Locations</RouterLink
        ><RouterLink :to="`/collections/${collectionId}/settings`"
          >Settings</RouterLink
        >
      </nav>
      <div v-if="locations.tree.length" class="management-layout">
        <aside class="management-sidebar panel" aria-label="Location tree">
          <h2>Storage tree</h2>
          <ul class="location-tree">
            <LocationTreeNode v-for="node in locations.tree" :key="node.id" :node="node" :selected-id="selected?.id ?? null" @select="selectNode" />
          </ul>
        </aside>
        <section class="management-panel panel" aria-labelledby="selected-location-heading">
          <template v-if="selected">
            <p class="eyebrow">Selected location</p><h2 id="selected-location-heading">{{ selected.name }}</h2>
            <dl class="metadata-grid"><div><dt>Type</dt><dd>{{ selected ? typeLabels[selected.type] : '' }}</dd></div><div><dt>Parent</dt><dd>{{ selected?.parent_id === null ? 'Root location' : parentOptions.find((option) => option.id === selected?.parent_id)?.path ?? 'Location' }}</dd></div><div v-if="selected?.description"><dt>Description</dt><dd>{{ selected.description }}</dd></div></dl>
            <div v-if="canEdit" class="action-row management-actions"><button type="button" class="button-secondary" :aria-label="`Edit ${selected.name}`" @click="startEdit(selected)">Edit location</button><button type="button" class="button-secondary" :aria-label="`Add child to ${selected.name}`" @click="startChild(selected)">Add child</button><button type="button" class="button-danger button-icon" :aria-label="`Delete ${selected.name}`" title="Delete location" :disabled="selected.children.length > 0" @click="deleting = selected"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 7h14M10 11v6m4-6v6M9 7l1-2h4l1 2m-8 0 1 13h8l1-13" /></svg></button></div>
            <p v-if="canEdit && selected.children.length" class="location-node__hint">Move or remove child locations before deleting.</p>
          </template>
          <div v-else class="empty-state location-detail-empty">
            <h2 id="selected-location-heading">No location selected</h2>
            <p>Select a location to view or edit its details.</p>
          </div>
        </section>
      </div>
      <form
        v-if="creatingRoot"
        class="collection-form panel modal-panel"
        @submit.prevent="saveCreate"
      >
        <h2>Add root location</h2>
        <label>Name<input v-model="name" required maxlength="255" /></label
        ><label
          >Type<select v-model="type">
            <option
              v-for="locationType in locationTypes"
              :key="locationType"
              :value="locationType"
            >
              {{ typeLabels[locationType] }}
            </option>
          </select></label
        ><label
          >Description <span class="optional">optional</span
          ><textarea v-model="description" rows="3" />
        </label>
        <div class="action-row">
          <button type="submit" :disabled="busy">
            {{ busy ? "Saving…" : "Add location" }}</button
          ><button
            type="button"
            class="button-secondary"
            @click="creatingRoot = false"
          >
            Cancel
          </button>
        </div>
      </form>
      <form
        v-if="childParent"
        class="collection-form panel modal-panel"
        @submit.prevent="saveCreate"
      >
        <h2>Add child to {{ childParent.name }}</h2>
        <label>Name<input v-model="name" required maxlength="255" /></label
        ><label
          >Type<select v-model="type">
            <option
              v-for="locationType in locationTypes"
              :key="locationType"
              :value="locationType"
            >
              {{ typeLabels[locationType] }}
            </option>
          </select></label
        ><label
          >Description <span class="optional">optional</span
          ><textarea v-model="description" rows="3" />
        </label>
        <div class="action-row">
          <button type="submit" :disabled="busy">
            {{ busy ? "Saving…" : "Add child" }}</button
          ><button
            type="button"
            class="button-secondary"
            @click="childParent = null"
          >
            Cancel
          </button>
        </div>
      </form>
      <form
        v-if="editing"
        class="collection-form panel"
        @submit.prevent="saveEdit"
      >
        <h2>Edit {{ editing.name }}</h2>
        <label>Name<input v-model="name" required maxlength="255" /></label
        ><label
          >Type<select v-model="type">
            <option
              v-for="locationType in locationTypes"
              :key="locationType"
              :value="locationType"
            >
              {{ typeLabels[locationType] }}
            </option>
          </select></label
        ><label
          >Description <span class="optional">optional</span
          ><textarea v-model="description" rows="3" /></label
        ><label
          >Parent<select v-model="parentId">
            <option :value="null">No parent / Root</option>
            <option
              v-for="option in parentOptions"
              :key="option.id"
              :value="option.id"
            >
              {{ option.path }}
            </option>
          </select></label
        >
        <div class="action-row">
          <button type="submit" :disabled="busy">
            {{ busy ? "Saving…" : "Save changes" }}</button
          ><button
            type="button"
            class="button-secondary"
            @click="editing = null"
          >
            Cancel
          </button>
        </div>
      </form>
      <p v-if="actionError" class="form-error" role="alert">
        {{ actionError }}
      </p>
      <div v-if="locations.tree.length === 0" class="empty-state">
        <h2>No locations yet</h2>
        <p v-if="canEdit">
          Create a root location to start your physical storage tree.
        </p>
        <p v-else>No locations have been created for this collection.</p>
      </div>
      <section
        v-if="deleting"
        class="confirmation panel"
        aria-labelledby="delete-location-heading"
      >
        <h2 id="delete-location-heading">Delete {{ deleting.name }}?</h2>
        <p>
          This deletes this location only. Child locations must be moved or
          removed first.
        </p>
        <div class="action-row">
          <button
            type="button"
            class="button-danger"
            :disabled="busy"
            @click="confirmDelete"
          >
            {{ busy ? "Deleting…" : "Confirm delete" }}</button
          ><button
            type="button"
            class="button-secondary"
            :disabled="busy"
            @click="deleting = null"
          >
            Cancel
          </button>
        </div>
      </section>
    </template>
  </section>
</template>
