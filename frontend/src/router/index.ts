import { createRouter, createWebHistory } from 'vue-router'

import HealthView from '@/views/HealthView.vue'
import CollectionDetailView from '@/views/CollectionDetailView.vue'
import CollectionsView from '@/views/CollectionsView.vue'
import AdminUsersView from '@/views/AdminUsersView.vue'
import LoginView from '@/views/LoginView.vue'
import SetupView from '@/views/SetupView.vue'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'health',
      component: HealthView,
    },
    { path: '/login', name: 'login', component: LoginView },
    { path: '/setup', name: 'setup', component: SetupView },
    { path: '/collections', name: 'collections', component: CollectionsView },
    { path: '/admin/users', name: 'admin-users', component: AdminUsersView, meta: { requiresInstanceAdmin: true } },
    {
      path: '/collections/:collectionId',
      name: 'collection-detail',
      component: CollectionDetailView,
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.ready) await auth.bootstrap()
  if (auth.setupRequired && to.name !== 'setup') return { name: 'setup' }
  if (!auth.setupRequired && !auth.user && to.name !== 'login') return { name: 'login' }
  if (auth.user && (to.name === 'login' || to.name === 'setup')) return { name: 'health' }
  if (to.meta.requiresInstanceAdmin && !auth.user?.is_instance_admin) return { name: 'collections' }
  return true
})
export default router
