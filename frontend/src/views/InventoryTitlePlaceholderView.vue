<template>
  <section class="page-content workspace-content">
    <div class="empty-state">
      <h1>Title details</h1>
      <p>Title details will be available in the next inventory update.</p>
      <RouterLink class="button-secondary" :to="{ name: 'inventory', params: { collectionId: $route.params.collectionId } }">Back to Inventory</RouterLink>
    </div>
  </section>
</template>
