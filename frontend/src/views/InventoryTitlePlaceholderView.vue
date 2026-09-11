<script setup lang="ts">
import { computed, watch } from "vue";
import { useRoute } from "vue-router";
import { ApiError } from "@/api/client";
import type { InventoryItem } from "@/api/inventory";
import type { LocationTreeNode } from "@/api/locations";
import { useCollectionsStore } from "@/stores/collections";
import { useLibraryStore } from "@/stores/library";
import { useLocationsStore } from "@/stores/locations";

const route = useRoute();
const collections = useCollectionsStore();
const library = useLibraryStore();
const locations = useLocationsStore();
const collectionId = computed(() => Number(route.params.collectionId));
const entryId = computed(() => Number(route.params.catalogEntryId));
const canEdit = computed(() =>
  ["owner", "admin", "editor"].includes(collections.collection?.role ?? ""),
);

function flatten(nodes: LocationTreeNode[], prefix = ""): { id: number; path: string }[] {
  return nodes.flatMap((node) => {
    const path = prefix ? `${prefix} > ${node.name}` : node.name;
    return [{ id: node.id, path }, ...flatten(node.children, path)];
  });
}

const locationPaths = computed(() => new Map(flatten(locations.tree).map((location) => [location.id, location.path])));
function locationPath(copy: InventoryItem) {
  if (copy.location_id === null) return "Unassigned";
  return locationPaths.value.get(copy.location_id) ?? "Assigned";
}
function copiesFor(copies: InventoryItem[]) {
  return [...copies].sort((first, second) => first.created_at.localeCompare(second.created_at) || first.id - second.id);
}
function titleType(type: string) {
  return type.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
function detailError() {
  if (library.error instanceof ApiError && library.error.status === 404) return "This title is not available.";
  return "This title could not be loaded. Please try again.";
}
async function load() {
  await Promise.all([
    collections.loadCollection(collectionId.value),
    locations.loadTree(collectionId.value),
    library.loadDetail(collectionId.value, entryId.value),
  ]);
}
watch(() => [route.params.collectionId, route.params.catalogEntryId], load, { immediate: true });
</script>

<template>
  <section class="page-content workspace-content inventory-title-detail">
    <RouterLink class="back-link" :to="{ name: 'inventory', params: { collectionId } }">← Back to Inventory</RouterLink>
    <p v-if="library.error" class="form-error" role="alert">{{ detailError() }}</p>
    <template v-else-if="library.title">
      <header class="inventory-title-detail__header panel">
        <div class="inventory-title-detail__cover library-card__cover" aria-hidden="true">Stashive</div>
        <div class="inventory-title-detail__heading">
          <p v-if="collections.collection" class="eyebrow">{{ collections.collection.name }} · Inventory</p>
          <h1>{{ library.title.catalog_entry.display_title }}</h1>
          <p v-if="library.title.catalog_entry.sort_title" class="inventory-title-detail__sort-title">Sort title: {{ library.title.catalog_entry.sort_title }}</p>
          <p class="inventory-title-detail__type">{{ titleType(library.title.catalog_entry.type) }}</p>
          <p v-if="library.title.catalog_entry.notes" class="inventory-title-detail__notes">{{ library.title.catalog_entry.notes }}</p>
          <div v-if="canEdit" class="action-row inventory-title-detail__actions">
            <RouterLink class="button-secondary button-link" :to="{ name: 'inventory-title-edit', params: { collectionId, catalogEntryId: entryId } }">Edit title</RouterLink>
            <RouterLink class="button-secondary button-link" :to="{ name: 'inventory-edition-new', params: { collectionId, catalogEntryId: entryId } }">Add edition</RouterLink>
          </div>
        </div>
      </header>

      <section class="inventory-title-detail__editions" aria-label="Editions">
        <article v-for="edition in library.title.editions" :key="edition.id" class="edition-detail-card panel">
          <header class="edition-detail-card__header">
            <h2>{{ edition.display_name || "Standard Edition" }}</h2>
            <span v-if="edition.media_format" class="edition-format-badge">{{ edition.media_format }}</span>
            <RouterLink v-if="canEdit" class="button-secondary button-compact button-link" :to="{ name: 'inventory-edition-edit', params: { collectionId, catalogEntryId: entryId, editionId: edition.id } }">Edit edition</RouterLink>
          </header>
          <div v-if="edition.release_date || edition.region || edition.language || edition.publisher" class="edition-detail-card__metadata">
            <p v-if="edition.release_date || edition.region || edition.language">{{ [edition.release_date, edition.region && `Region ${edition.region}`, edition.language].filter(Boolean).join(" · ") }}</p>
            <p v-if="edition.publisher">{{ edition.publisher }}</p>
          </div>
          <section class="edition-detail-card__section">
            <h3>Barcodes &amp; IDs</h3>
            <p v-if="!edition.identifiers.length" class="state-message">No barcodes or IDs.</p>
            <ul v-else class="identifier-read-list">
              <li v-for="identifier in edition.identifiers" :key="identifier.id"><strong>{{ identifier.type }}</strong><span>{{ identifier.value }}</span><small v-if="identifier.source">{{ identifier.source }}</small></li>
            </ul>
          </section>
          <section class="edition-detail-card__section">
            <h3>Physical copies</h3>
            <p v-if="!edition.copies.length" class="state-message">No physical copies.</p>
            <ol v-else class="copy-read-list">
              <li v-for="(copy, index) in copiesFor(edition.copies)" :key="copy.id" class="copy-read-card">
                <h4>Copy {{ index + 1 }}</h4>
                <dl>
                  <div><dt>Location</dt><dd>{{ locationPath(copy) }}</dd></div>
                  <div v-if="copy.condition"><dt>Condition</dt><dd>{{ copy.condition }}</dd></div>
                  <div v-if="copy.notes"><dt>Notes</dt><dd>{{ copy.notes }}</dd></div>
                </dl>
              </li>
            </ol>
          </section>
        </article>
        <div v-if="!library.title.editions.length" class="empty-state"><h2>No editions</h2><p>This title does not have any editions yet.</p></div>
      </section>
    </template>
  </section>
</template>
