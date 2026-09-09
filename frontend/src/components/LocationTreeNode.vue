<script setup lang="ts">
import type { LocationTreeNode } from '@/api/locations'

defineOptions({ name: 'LocationTreeNode' })
defineProps<{ node: LocationTreeNode; canEdit: boolean }>()
defineEmits<{ addChild: [LocationTreeNode]; edit: [LocationTreeNode]; remove: [LocationTreeNode] }>()

const locationTypeLabels = {
  room: 'Room', cabinet: 'Cabinet', shelf: 'Shelf', box: 'Box', drawer: 'Drawer', other: 'Other',
} as const
</script>

<template>
  <li class="location-node">
    <div class="location-node__content">
      <div><strong>{{ node.name }}</strong> <span class="role-pill">{{ locationTypeLabels[node.type] }}</span>
        <p v-if="node.description" class="location-node__description">{{ node.description }}</p>
      </div>
      <div v-if="canEdit" class="action-row location-node__actions">
        <button type="button" class="button-secondary button-compact" @click="$emit('addChild', node)">Add child</button>
        <button type="button" class="button-secondary button-compact" @click="$emit('edit', node)">Edit</button>
        <button type="button" class="button-danger button-compact" :disabled="node.children.length > 0" @click="$emit('remove', node)">Delete</button>
      </div>
    </div>
    <p v-if="canEdit && node.children.length > 0" class="location-node__hint">Move or remove child locations before deleting.</p>
    <ul v-if="node.children.length" class="location-tree">
      <LocationTreeNode v-for="child in node.children" :key="child.id" :node="child" :can-edit="canEdit" @add-child="$emit('addChild', $event)" @edit="$emit('edit', $event)" @remove="$emit('remove', $event)" />
    </ul>
  </li>
</template>
