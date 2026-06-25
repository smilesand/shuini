<script setup lang="ts">
import { computed } from 'vue'
import ImportDataPanel from './ImportDataPanel.vue'

const props = defineProps<{
  importedValues: Record<string, unknown>
  category: 'hpc' | 'uhpc'
}>()

const showImport = defineModel<boolean>({ default: false })

const hasImport = computed(() => Object.keys(props.importedValues).length > 0)
</script>

<template>
  <template v-if="hasImport">
    <div style="display:flex;gap:6px;margin-bottom:12px">
      <el-button size="small" :type="showImport ? 'default' : 'primary'" @click="showImport = false">汇总值</el-button>
      <el-button size="small" :type="showImport ? 'primary' : 'default'" @click="showImport = true">导入值</el-button>
    </div>

    <ImportDataPanel v-if="showImport" :imported-values="importedValues" :category="category" />
  </template>
</template>
