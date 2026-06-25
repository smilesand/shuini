<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  importedValues: Record<string, unknown>
  category: 'hpc' | 'uhpc'
}>()

// ── HPC Excel 主键 ──────────────────────────────────────────────
const HPC_KEYS: { section: string; keys: string[] }[] = [
  { section: '性能要求', keys: ['fcuk', 'req_spread', 'req_slump'] },
  { section: '原材料性能', keys: ['fb', 'max_aggregate_size', 'rhoc', 'rho1', 'rho2', 'rho3', 'rho4', 'rhog', 'rhos'] },
  { section: '关键参数', keys: ['wb', 'bc', 'b1p', 'b2p', 'b3p', 'b4p', 'mb', 'sand_ratio', 'vg', 'alpha', 'air_content'] },
  { section: '实验室配合比', keys: ['mc', 'm1', 'm2', 'm3', 'm4', 'mg', 'ms', 'mw', 'ma', 'total_mass'] },
]

// ── UHPC Excel 主键 ──────────────────────────────────────────────
const UHPC_KEYS: { section: string; keys: string[] }[] = [
  { section: '性能要求', keys: ['fcuk', 'req_spread', 'tensile_strength', 'fiber_strength_grade'] },
  { section: '原材料性能', keys: ['cement_density', 'fly_ash_density', 'micro_bead_density', 'silica_fume_density', 'sand_density', 'steel_fiber_density', 'max_particle_size', 'min_particle_size', 'distribution_index', 'fly_ash_peak_size', 'fly_ash_accumulation_size', 'micro_bead_peak_size', 'micro_bead_silica_fume_ratio'] },
  { section: '关键参数', keys: ['wb', 'b1p', 'b3p', 'b4p', 'mb', 'alpha', 'sand_binder_ratio', 'steel_fiber_volume_ratio', 'micro_powder_coefficient', 'assumed_mix_mass'] },
  { section: '实验室配合比', keys: ['mc', 'm1', 'm3', 'm4', 'ms', 'msf', 'mw', 'ma', 'total_mass'] },
]

const SECTIONS = props.category === 'uhpc' ? UHPC_KEYS : HPC_KEYS

const LAB_MIX_KEYS = new Set(['mc', 'm1', 'm2', 'm3', 'm4', 'mg', 'ms', 'msf', 'mw', 'ma', 'total_mass'])

const HIGHLIGHT_KEYS: Record<string, Set<string>> = {
  hpc: new Set(['wb', 'sand_ratio', 'vg']),
  uhpc: new Set(['wb', 'sand_binder_ratio', 'msf']),
}

const LABEL_MAP: Record<string, string> = {
  fcuk: '强度等级', req_spread: '扩展度', req_slump: '坍落度', tensile_strength: '抗拉强度',
  fiber_strength_grade: '钢纤维抗拉等级', fb: '胶材28d强度', max_aggregate_size: '粗骨料最大粒径',
  rhoc: '水泥密度', rho1: '粉煤灰密度', rho2: '矿粉密度', rho3: '微珠密度', rho4: '硅灰密度',
  rhog: '粗骨料密度', rhos: '细骨料密度',
  cement_density: '水泥密度', fly_ash_density: '粉煤灰密度', micro_bead_density: '微珠密度',
  silica_fume_density: '硅灰密度', sand_density: '细骨料密度', steel_fiber_density: '钢纤维密度',
  max_particle_size: '体系最大粒径', min_particle_size: '最小粒径', distribution_index: '分布指数',
  fly_ash_peak_size: '粉煤灰峰值粒径', fly_ash_accumulation_size: '粉煤灰累积粒径',
  micro_bead_peak_size: '微珠峰值粒径', micro_bead_silica_fume_ratio: '微珠硅灰比',
  wb: '水胶比', bc: '水泥占比', b1p: '粉煤灰占比', b2p: '矿粉占比', b3p: '微珠占比', b4p: '硅灰占比',
  mb: '胶材总量', sand_ratio: '砂率', sand_binder_ratio: '砂胶比', vg: '粗骨料体积',
  alpha: '外加剂掺量', air_content: '含气量', steel_fiber_volume_ratio: '钢纤维体积掺量',
  micro_powder_coefficient: '微粉系数', assumed_mix_mass: '假定混合质量',
  mc: '水泥', m1: '粉煤灰', m2: '矿粉', m3: '微珠', m4: '硅灰',
  mg: '粗骨料', ms: '细骨料', msf: '钢纤维', mw: '水', ma: '外加剂', total_mass: '合计',
}

const highlightSet = computed(() => HIGHLIGHT_KEYS[props.category])

const sections = computed(() => {
  return SECTIONS.map(s => {
    const isLab = s.section === '实验室配合比'
    const rows = s.keys
      .map(k => ({ key: k, label: LABEL_MAP[k] || k, value: props.importedValues[k], is20L: isLab && LAB_MIX_KEYS.has(k), highlight: highlightSet.value.has(k) }))
      .filter(r => r.value !== null && r.value !== undefined)
    return { section: s.section, rows, isLab }
  }).filter(s => s.rows.length > 0)
})

const UNIT_MAP: Record<string, string> = {
  // 性能
  fcuk: 'MPa', req_spread: 'mm', req_slump: 'mm', tensile_strength: 'MPa',
  fiber_strength_grade: '', fb: 'MPa',
  // 原材料 — 密度
  rhoc: 'kg/m³', rho1: 'kg/m³', rho2: 'kg/m³', rho3: 'kg/m³', rho4: 'kg/m³',
  rhog: 'kg/m³', rhos: 'kg/m³',
  cement_density: 'kg/m³', fly_ash_density: 'kg/m³', micro_bead_density: 'kg/m³',
  silica_fume_density: 'kg/m³', sand_density: 'kg/m³', steel_fiber_density: 'kg/m³',
  // 原材料 — 粒径
  max_aggregate_size: 'mm', max_particle_size: 'µm', min_particle_size: 'µm',
  fly_ash_peak_size: 'µm', fly_ash_accumulation_size: 'µm', micro_bead_peak_size: 'µm',
  // 无量纲
  distribution_index: '', micro_bead_silica_fume_ratio: '', wb: '', sand_binder_ratio: '',
  micro_powder_coefficient: '',
  // 百分比
  bc: '%', b1p: '%', b2p: '%', b3p: '%', b4p: '%', sand_ratio: '%',
  alpha: '%', air_content: '%', steel_fiber_volume_ratio: '%',
  // 质量
  mb: 'kg', mc: 'kg', m1: 'kg', m2: 'kg', m3: 'kg', m4: 'kg',
  mg: 'kg', ms: 'kg', msf: 'kg', mw: 'kg', ma: 'kg', total_mass: 'kg',
  // 其他
  vg: 'm³', assumed_mix_mass: 'kg/m³',
}

function fmtVal(r: { key: string; value: unknown; is20L?: boolean }): string {
  const v = r.value
  const unit = UNIT_MAP[r.key]
  if (typeof v === 'number') {
    const num = Number.isInteger(v) ? String(v) : Number(v.toFixed(2)).toString()
    return unit ? `${num} ${unit}` : num
  }
  const s = String(v ?? '')
  return unit ? `${s} ${unit}` : s
}

function fmt20L(r: { key: string; value: unknown; is20L?: boolean }): string {
  if (!r.is20L || typeof r.value !== 'number') return ''
  const v20 = Number((r.value / 50).toFixed(2))
  const unit = UNIT_MAP[r.key]
  return unit ? `${v20} ${unit}` : String(v20)
}
</script>

<template>
  <template v-if="sections.length">
    <div v-for="s in sections" :key="s.section" class="summary-group">
      <div class="group-label">{{ s.isLab ? s.section + '（每方 → 20L）' : s.section }}</div>
      <div v-for="r in s.rows" :key="r.key" class="summary-row" :class="{ 'highlight-row': r.highlight }">
        <span class="row-label">{{ r.label }}</span>
        <span class="row-val">
          {{ fmtVal(r) }}
          <small v-if="r.is20L">20L: {{ fmt20L(r) }}</small>
        </span>
      </div>
    </div>
  </template>
  <el-empty v-else description="无导入数据" :image-size="48" style="padding:12px 0" />
</template>

<style scoped>
.summary-group {
  padding: 8px 0;
  border-bottom: 1px solid #f0f2f5;
}
.summary-group:last-child {
  border-bottom: none;
}
.group-label {
  font-size: 11px; font-weight: 700;
  color: #2a5298; text-transform: uppercase;
  letter-spacing: 0.5px; margin-bottom: 4px;
}
.summary-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}
.row-label {
  font-size: 12px;
  color: #555;
  font-weight: 600;
}
.row-val {
  font-size: 13px;
  font-weight: 700;
  color: #333;
}
.row-val small {
  font-size: 10px; color: #999; font-weight: 400; margin-left: 4px;
}
.highlight-row {
  background: linear-gradient(135deg, #fffef5, #fff7c0);
  border-radius: 4px;
}
.highlight-row .row-label {
  color: #2a5298;
}
</style>
