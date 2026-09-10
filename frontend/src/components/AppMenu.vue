<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const router = useRouter();
const menu = ref<HTMLDetailsElement | null>(null);
const open = ref(false);
function closeMenu(): void {
  menu.value?.removeAttribute("open");
  open.value = false;
}
function onToggle(): void {
  open.value = menu.value?.open ?? false;
}
function onPointerDown(event: PointerEvent): void {
  if (menu.value && !menu.value.contains(event.target as Node)) closeMenu();
}
function onKeyDown(event: KeyboardEvent): void {
  if (event.key === "Escape") closeMenu();
}
async function signOut(): Promise<void> {
  closeMenu();
  await auth.signOut();
  await router.push({ name: "login" });
}
onMounted(() => {
  document.addEventListener("pointerdown", onPointerDown);
  document.addEventListener("keydown", onKeyDown);
});
onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", onPointerDown);
  document.removeEventListener("keydown", onKeyDown);
});
</script>

<template>
  <details ref="menu" class="app-menu" @toggle="onToggle">
    <summary
      class="app-menu__trigger"
      aria-label="Open application menu"
      :aria-expanded="open"
      @click="open = !open"
    >
      <span class="app-menu__username">{{ auth.user?.username }}</span
      ><span aria-hidden="true">☰</span>
    </summary>
    <nav class="app-menu__popover" aria-label="Application menu">
      <strong>{{ auth.user?.display_name || auth.user?.username }}</strong>
      <RouterLink to="/collections" @click="closeMenu">Collections</RouterLink>
      <RouterLink
        v-if="auth.user?.is_instance_admin"
        to="/admin/users"
        @click="closeMenu"
        >Administration</RouterLink
      >
      <button type="button" class="app-menu__signout" @click="signOut">
        Sign out
      </button>
    </nav>
  </details>
</template>
