<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import AppMenu from '@/components/AppMenu.vue'

const auth = useAuthStore()
</script>

<template>
  <main class="application-shell">
    <header v-if="auth.user" class="application-header">
      <RouterLink class="brand" :to="auth.user ? '/collections' : '/'" aria-label="Stashive home">Stashive</RouterLink>
      <span class="brand-tagline">Physical collections, organized.</span>
      <AppMenu />
    </header>
    <RouterView />
  </main>
</template>
