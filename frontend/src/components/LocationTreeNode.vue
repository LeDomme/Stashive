<script setup lang="ts">
import type { LocationTreeNode } from "@/api/locations";

defineOptions({ name: "LocationTreeNode" });
defineProps<{ node: LocationTreeNode; selectedId: number | null }>();
defineEmits<{ select: [LocationTreeNode] }>();

const locationTypeLabels = {
  room: "Room",
  cabinet: "Cabinet",
  shelf: "Shelf",
  box: "Box",
  drawer: "Drawer",
  other: "Other",
} as const;
</script>

<template>
  <li class="location-node">
    <button type="button" class="location-node__content" :class="{ 'is-selected': selectedId === node.id }" :aria-pressed="selectedId === node.id" @click="$emit('select', node)">
      <div class="location-node__row">
        <strong class="location-node__name">{{ node.name }}</strong>
        <span class="location-type-badge">{{ locationTypeLabels[node.type] }}</span>
        <p v-if="node.description" class="location-node__description">
          {{ node.description }}
        </p>
      </div>
    </button>
    <ul v-if="node.children.length" class="location-tree">
      <LocationTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :selected-id="selectedId"
        @select="$emit('select', $event)"
      />
    </ul>
  </li>
</template>
