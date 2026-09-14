<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps<{
  id: string
  label: string
  modelValue: string[]
  presets: string[]
  disabled?: boolean
}>()
const emit = defineEmits<{ 'update:modelValue': [values: string[]] }>()

const customValue = ref('')
const open = ref(false)
const root = ref<HTMLElement | null>(null)
const trigger = ref<HTMLButtonElement | null>(null)
const selectedValues = computed(() => props.modelValue)
const summary = computed(() => {
  if (!selectedValues.value.length) return `Select ${props.label.toLowerCase()}...`
  const [first, second, ...remaining] = selectedValues.value
  return [first, second, remaining.length ? `+${remaining.length}` : ''].filter(Boolean).join(', ')
})

function includesValue(values: string[], value: string) {
  return values.some((candidate) => candidate.trim() === value.trim())
}

function addValue(value: string) {
  const normalized = value.trim()
  if (!normalized || includesValue(selectedValues.value, normalized)) return false
  emit('update:modelValue', [...selectedValues.value, normalized])
  return true
}

function togglePreset(value: string, selected: boolean) {
  if (selected) addValue(value)
  else removeValue(value)
}

function removeValue(value: string) {
  emit(
    'update:modelValue',
    selectedValues.value.filter((candidate) => candidate !== value),
  )
}

function addCustomValue() {
  if (addValue(customValue.value)) customValue.value = ''
}

async function togglePopover() {
  open.value = !open.value
  if (open.value) await nextTick()
}

function closePopover() {
  if (!open.value) return
  open.value = false
  void nextTick(() => trigger.value?.focus())
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') closePopover()
}

function onDocumentClick(event: MouseEvent) {
  if (root.value && !root.value.contains(event.target as Node)) open.value = false
}

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
  document.addEventListener('click', onDocumentClick)
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  document.removeEventListener('click', onDocumentClick)
})
</script>

<template>
  <div ref="root" class="multi-preset-field" :class="{ 'is-open': open }">
    <span :id="`${id}-label`" class="multi-preset-field__label">{{ label }}</span>
    <button
      :id="id"
      ref="trigger"
      type="button"
      class="multi-preset-field__trigger"
      :aria-controls="`${id}-popover`"
      :aria-expanded="open"
      :aria-labelledby="`${id}-label ${id}-summary`"
      :disabled="disabled"
      @click="togglePopover"
    >
      <span :id="`${id}-summary`">{{ summary }}</span><span aria-hidden="true">▾</span>
    </button>
    <div v-if="open" :id="`${id}-popover`" class="multi-preset-field__popover" role="group" :aria-labelledby="`${id}-label`">
      <div v-if="selectedValues.length" class="multi-preset-field__selected" :aria-label="`Selected ${label}`">
        <span v-for="value in selectedValues" :key="value" class="multi-preset-field__chip">
          {{ value }}
          <button type="button" class="button-ghost button-compact" :aria-label="`Remove ${value}`" @click="removeValue(value)">Remove</button>
        </span>
      </div>
      <div v-if="presets.length" class="multi-preset-field__presets">
        <label v-for="preset in presets" :key="preset" class="multi-preset-field__option">
          <input type="checkbox" :checked="includesValue(selectedValues, preset)" @change="togglePreset(preset, ($event.target as HTMLInputElement).checked)" />
          {{ preset }}
        </label>
      </div>
      <p v-else class="field-hint">No presets are available for this media format. You can add a custom value.</p>
      <div class="multi-preset-field__custom">
        <label :for="`${id}-custom`">Add custom {{ label.toLowerCase() }}</label>
        <input :id="`${id}-custom`" v-model="customValue" @keydown.enter.prevent="addCustomValue" />
        <button type="button" class="button-secondary button-compact" @click="addCustomValue">Add</button>
      </div>
    </div>
  </div>
</template>
