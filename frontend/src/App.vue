<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
</script>

<template>
  <main class="application-shell">
    <header class="application-header">
      <RouterLink class="brand" :to="auth.user ? '/collections' : '/'" aria-label="Stashive home">Stashive</RouterLink>
      <span class="brand-tagline">Physical collections, organized.</span>
      <nav v-if="auth.user" class="application-nav" aria-label="Main navigation">
        <RouterLink to="/collections">Collections</RouterLink>
        <RouterLink v-if="auth.user.is_instance_admin" to="/admin/users">Users</RouterLink>
      </nav>
    </header>
    <RouterView />
  </main>
</template>
