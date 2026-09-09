<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { fetchHealth } from '@/api/health'

type ConnectionState = 'checking' | 'available' | 'unavailable'

const connectionState = ref<ConnectionState>('checking')

onMounted(async () => {
  try {
    const health = await fetchHealth()
    connectionState.value = health.status === 'ok' ? 'available' : 'unavailable'
  } catch {
    connectionState.value = 'unavailable'
  }
})
</script>

<template>
  <section class="status-card" aria-labelledby="status-heading">
    <p class="eyebrow">Repository foundation</p>
    <h1 id="status-heading">Stashive is ready to grow.</h1>
    <p>
      The application shell is running. Domain features will appear here as their milestones are
      implemented.
    </p>
    <p class="connection-status" :data-state="connectionState" aria-live="polite">
      API connection:
      <strong v-if="connectionState === 'checking'">checking</strong>
      <strong v-else-if="connectionState === 'available'">available</strong>
      <strong v-else>unavailable</strong>
    </p>
  </section>
</template>
