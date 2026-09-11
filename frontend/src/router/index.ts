import { createRouter, createWebHistory } from 'vue-router'

import CollectionSettingsView from '@/views/CollectionSettingsView.vue'
import CollectionsView from '@/views/CollectionsView.vue'
import AdminUsersView from '@/views/AdminUsersView.vue'
import LoginView from '@/views/LoginView.vue'
import LocationsView from '@/views/LocationsView.vue'
import CatalogView from '@/views/CatalogView.vue'
import CatalogDetailView from '@/views/CatalogDetailView.vue'
import InventoryView from '@/views/InventoryView.vue'
import InventoryTitlePlaceholderView from '@/views/InventoryTitlePlaceholderView.vue'
import InventoryTitleManagementView from '@/views/InventoryTitleManagementView.vue'
import InventoryEditionManagementView from '@/views/InventoryEditionManagementView.vue'
import SetupView from '@/views/SetupView.vue'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: { name: 'collections' },
    },
    { path: '/login', name: 'login', component: LoginView },
    { path: '/setup', name: 'setup', component: SetupView },
    { path: '/collections', name: 'collections', component: CollectionsView },
    {
      path: '/collections/:collectionId/locations',
      name: 'locations',
      component: LocationsView,
    },
    { path: '/collections/:collectionId/catalog', name: 'catalog', component: CatalogView },
    { path: '/collections/:collectionId/catalog/:entryId', name: 'catalog-detail', component: CatalogDetailView },
    { path: '/collections/:collectionId/inventory', name: 'inventory', component: InventoryView },
    { path: '/collections/:collectionId/inventory/:catalogEntryId/edit', name: 'inventory-title-edit', component: InventoryTitleManagementView },
    { path: '/collections/:collectionId/inventory/:catalogEntryId/editions/new', name: 'inventory-edition-new', component: InventoryEditionManagementView },
    { path: '/collections/:collectionId/inventory/:catalogEntryId/editions/:editionId/edit', name: 'inventory-edition-edit', component: InventoryEditionManagementView },
    { path: '/collections/:collectionId/inventory/:catalogEntryId', name: 'inventory-title', component: InventoryTitlePlaceholderView },
    { path: '/collections/:collectionId/settings', name: 'collection-settings', component: CollectionSettingsView },
    { path: '/admin/users', name: 'admin-users', component: AdminUsersView, meta: { requiresInstanceAdmin: true } },
    {
      path: '/collections/:collectionId',
      redirect: (to) => ({ name: 'inventory', params: { collectionId: to.params.collectionId } }),
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.ready) await auth.bootstrap()
  if (auth.setupRequired && to.name !== 'setup') return { name: 'setup' }
  if (!auth.setupRequired && !auth.user && to.name !== 'login') return { name: 'login' }
  if (auth.user && (to.name === 'login' || to.name === 'setup')) return { name: 'collections' }
  if (to.meta.requiresInstanceAdmin && !auth.user?.is_instance_admin) return { name: 'collections' }
  return true
})
export default router
