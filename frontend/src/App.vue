<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";

import { useAuthStore } from "@/stores/auth";
import AppMenu from "@/components/AppMenu.vue";

const auth = useAuthStore();
const route = useRoute();
const headerBackLink = computed(() => {
  const collectionId = route.params.collectionId;
  const catalogEntryId = route.params.catalogEntryId;
  const name = String(route.name ?? "");
  if (!collectionId) return null;
  if (name === "catalog") return { label: "Back to Settings", to: { name: "collection-settings", params: { collectionId } } };
  if (name === "catalog-detail") return { label: "Back to advanced catalog", to: { name: "catalog", params: { collectionId } } };
  if (name === "inventory-add" || name === "inventory-title") return { label: "Back to Inventory", to: { name: "inventory", params: { collectionId } } };
  if (["inventory-title-edit", "inventory-edition-new", "inventory-edition-edit", "inventory-copy-new", "inventory-copy-edit"].includes(name) && catalogEntryId) {
    return { label: "Back to title", to: { name: "inventory-title", params: { collectionId, catalogEntryId } } };
  }
  return null;
});
</script>

<template>
  <main class="application-shell">
    <header v-if="auth.user" class="application-header">
      <div class="application-header__content">
        <RouterLink class="brand" to="/collections" aria-label="Stashive home">
          <img src="/stashive-logo.png" alt="" class="brand__logo" />
          <span
            ><strong>Stashive</strong
            ><small>Collect. Locate. Keep track.</small></span
          >
        </RouterLink>
        <RouterLink v-if="headerBackLink" class="header-back-link" :to="headerBackLink.to">{{ headerBackLink.label }}</RouterLink>
        <AppMenu />
      </div>
    </header>
    <RouterView />
  </main>
</template>
