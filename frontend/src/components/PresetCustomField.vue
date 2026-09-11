<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  id: string
  label: string
  modelValue: string | null
  presets: string[]
  allowEmpty?: boolean
  emptyLabel?: string
  customLabel?: string
  emptyValue?: string | null
}>(), { allowEmpty: false, emptyLabel: 'Not specified', customLabel: 'Other / Custom', emptyValue: null })
const emit = defineEmits<{ 'update:modelValue': [value: string | null] }>()
const custom = ref('')
const mode = ref('')
const customMode = '__custom__'
function sync(value: string | null) { if (value === null || value === '') { mode.value = ''; return }; if (props.presets.includes(value)) { mode.value = value; return }; mode.value = customMode; custom.value = value }
watch(() => props.modelValue, sync, { immediate: true })
const customId = computed(() => `${props.id}-custom`)
function select(value: string) { mode.value = value; if (value === customMode) emit('update:modelValue', custom.value || props.emptyValue); else emit('update:modelValue', value || props.emptyValue) }
function updateCustom(value: string) { custom.value = value; emit('update:modelValue', value || props.emptyValue) }
</script>
<template>
  <label :for="id">{{ label }}</label>
  <select :id="id" :value="mode" @change="select(($event.target as HTMLSelectElement).value)">
    <option v-if="allowEmpty" value="">{{ emptyLabel }}</option>
    <option v-for="preset in presets" :key="preset" :value="preset">{{ preset }}</option>
    <option :value="customMode">{{ customLabel }}</option>
  </select>
  <label v-if="mode === customMode" :for="customId">{{ customLabel }} {{ label }}</label>
  <input v-if="mode === customMode" :id="customId" :value="custom" @input="updateCustom(($event.target as HTMLInputElement).value)" />
</template>
