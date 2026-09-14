<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  id: string
  label: string
  modelValue: string[]
  presets: string[]
  disabled?: boolean
}>()
const emit = defineEmits<{ 'update:modelValue': [values: string[]] }>()

const customValue = ref('')
const selectedValues = computed(() => props.modelValue)

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
</script>

<template>
  <fieldset class="multi-preset-field" :disabled="disabled">
    <legend>{{ label }}</legend>
    <div v-if="selectedValues.length" class="multi-preset-field__selected" :aria-label="`Selected ${label}`">
      <span v-for="value in selectedValues" :key="value" class="multi-preset-field__chip">
        {{ value }}
        <button type="button" class="button-ghost button-compact" :aria-label="`Remove ${value}`" @click="removeValue(value)">Remove</button>
      </span>
    </div>
    <div v-if="presets.length" class="multi-preset-field__presets">
      <label v-for="preset in presets" :key="preset" class="multi-preset-field__option">
        <input
          type="checkbox"
          :checked="includesValue(selectedValues, preset)"
          @change="togglePreset(preset, ($event.target as HTMLInputElement).checked)"
        />
        {{ preset }}
      </label>
    </div>
    <p v-else class="field-hint">No presets are available for this media format. You can add a custom value.</p>
    <div class="multi-preset-field__custom">
      <label :for="`${id}-custom`">Add custom {{ label.toLowerCase() }}</label>
      <input :id="`${id}-custom`" v-model="customValue" @keydown.enter.prevent="addCustomValue" />
      <button type="button" class="button-secondary button-compact" @click="addCustomValue">Add</button>
    </div>
  </fieldset>
</template>
