<script setup lang="ts">
import { RouterLink, RouterView } from "vue-router";

import { useAuthStore } from "@/stores/auth";
import AppMenu from "@/components/AppMenu.vue";

const auth = useAuthStore();
</script>

<template>
  <main class="application-shell">
    <header v-if="auth.user" class="application-header">
      <RouterLink class="brand" to="/collections" aria-label="Stashive home">
        <img src="/stashive-logo.png" alt="" class="brand__logo" />
        <span
          ><strong>Stashive</strong
          ><small>Collect. Locate. Keep track.</small></span
        >
      </RouterLink>
      <AppMenu />
    </header>
    <RouterView />
  </main>
</template>
