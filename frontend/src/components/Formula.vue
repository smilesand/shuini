<script setup lang="ts">
import katex from 'katex'
import { computed } from 'vue'

const props = defineProps<{ latex: string; display?: boolean }>()

const html = computed(() => {
  try {
    return katex.renderToString(props.latex, {
      displayMode: props.display ?? true,
      throwOnError: false,
    })
  } catch {
    return props.latex
  }
})
</script>

<template>
  <div class="katex-formula" v-html="html" />
</template>

<style>
@import 'katex/dist/katex.min.css';
</style>

<style scoped>
.katex-formula {
  font-size: 15px;
}
</style>
