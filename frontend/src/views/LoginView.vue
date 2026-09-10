<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
const username = ref(''); const password = ref(''); const error = ref('')
const auth = useAuthStore(); const router = useRouter()
async function submit(): Promise<void> { try { await auth.signIn(username.value, password.value); await router.replace('/') } catch { error.value = 'Login failed. Check your credentials and try again.' } }
</script>
<template><section class="status-card"><p class="eyebrow">Local access</p><h1>Sign in to Stashive</h1><form class="auth-form" @submit.prevent="submit"><label>Username<input v-model="username" autocomplete="username" required /></label><label>Password<input v-model="password" type="password" autocomplete="current-password" required /></label><p v-if="error" role="alert">{{ error }}</p><button type="submit">Sign in</button></form></section></template>
