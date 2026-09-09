<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <main class="application-shell">
    <header class="application-header">
      <a class="brand" href="/" aria-label="Stashive home">Stashive</a>
      <span class="brand-tagline">Physical collections, organized.</span>
    </header>
    <RouterView />
  </main>
</template>
