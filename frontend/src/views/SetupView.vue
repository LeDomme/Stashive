<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
const token = ref(''); const username = ref(''); const displayName = ref(''); const password = ref(''); const error = ref('')
const auth = useAuthStore(); const router = useRouter()
async function submit(): Promise<void> { try { await auth.completeSetup(token.value, username.value, displayName.value, password.value); await router.replace('/') } catch { error.value = 'Setup failed. Check the token and entered credentials.' } }
</script>
<template><section class="status-card"><p class="eyebrow">First-run setup</p><h1>Create the first administrator.</h1><form class="auth-form" @submit.prevent="submit"><label>Setup token<input v-model="token" autocomplete="off" required /></label><label>Username<input v-model="username" autocomplete="username" required /></label><label>Display name<input v-model="displayName" autocomplete="name" /></label><label>Password<input v-model="password" type="password" autocomplete="new-password" minlength="12" required /></label><p v-if="error" role="alert">{{ error }}</p><button type="submit">Create administrator</button></form></section></template>
