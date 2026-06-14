<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import SidebarLayout from './components/SidebarLayout.vue'

const route = useRoute()
const isPublic = computed(() => route.meta['public'])
</script>

<template>
  <RouterView v-if="isPublic" />
  <SidebarLayout v-else />
</template>
