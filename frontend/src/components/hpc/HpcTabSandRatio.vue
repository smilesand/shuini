<script setup lang="ts">
import { watch } from 'vue'
import { useCalcStore } from '../../stores/calcStore.ts'
import { debounce } from '../../utils/debounce.ts'
import Formula from '../Formula.vue'
import '../../style/calc-tabs.css'

const emit = defineEmits<{ (e: 'next-step'): void }>()
const store = useCalcStore()

// 输入砂率后 600ms 自动确认（防抖）
const debouncedConfirm = debounce(() => store.confirmSandRatio(), 600)
watch(
  () => store.sandRatioInput,
  (val) => { if (val && val > 0) debouncedConfirm() },
)

const srTable = [
  { label: 'C80',  vals: ['45 ~ 49', '44 ~ 48', '43 ~ 47'] },
  { label: 'C90',  vals: ['43 ~ 47', '42 ~ 46', '41 ~ 45'] },
  { label: 'C100', vals: ['41 ~ 45', '40 ~ 44', '39 ~ 43'] },
]
const colLabels = ['16.0 mm', '20.0 mm', '25.0 mm']

// 恢复已持久化的行列选择
if (store.sandRatioCol !== null) {
  // 同时同步 maxAggregateSize（兼容旧数据）
  store.maxAggregateSize = colLabels[store.sandRatioCol] ?? null
}

function toggleRow(ri: number) {
  store.sandRatioRow = store.sandRatioRow === ri ? null : ri
}
function toggleCol(ci: number) {
  store.sandRatioCol = store.sandRatioCol === ci ? null : ci
  store.maxAggregateSize = store.sandRatioCol === null ? null : colLabels[store.sandRatioCol]
}
function cellClass(ri: number, ci: number) {
  const rowSel = store.sandRatioRow === ri
  const colSel = store.sandRatioCol === ci
  if (rowSel && colSel) return 'cell-cross'
  if (rowSel || colSel) return 'cell-highlight'
  return ''
}
function getRange(): string | null {
  if (store.sandRatioRow !== null && store.sandRatioCol !== null) {
    return srTable[store.sandRatioRow].vals[store.sandRatioCol]
  }
  return null
}
</script>

<template>
  <div>
    <!-- Section 1: 砂率参考表 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><Grid /></el-icon>
        砂率参考表
      </div>
      <div class="cs-section-body">
        <p style="font-size:12px;color:#909399;margin:0 0 10px">点击强度等级行或粗骨料最大粒径列，交叉高亮参考范围</p>
        <table class="sr-table">
          <thead>
            <tr>
              <th>强度等级</th>
              <th
                v-for="(col, ci) in colLabels"
                :key="ci"
                :class="{ 'head-selected': store.sandRatioCol === ci }"
                @click="toggleCol(ci)"
              >{{ col }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, ri) in srTable" :key="ri">
              <td
                class="row-label-cell"
                :class="{ 'row-selected': store.sandRatioRow === ri }"
                @click="toggleRow(ri)"
              >{{ row.label }}</td>
              <td
                v-for="(val, ci) in row.vals"
                :key="ci"
                :class="cellClass(ri, ci)"
                class="data-cell"
              >{{ val }}</td>
            </tr>
          </tbody>
        </table>

        <el-alert type="info" :closable="false" style="margin-bottom:10px">
          ① 本表数值系中砂选用砂率；对细砂或粗砂，可相应减少或增大砂率。<br>
          ② 采用机制砂配制混凝土时，砂率可适当增大。
        </el-alert>

        <el-alert
          v-if="getRange()"
          :title="`参考范围：${getRange()} %`"
          type="success"
          :closable="false"
          show-icon
        />
      </div>
    </div>

    <!-- Section 2: 确认砂率 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><EditPen /></el-icon>
        确认砂率
      </div>
      <div class="cs-section-body">
        <el-form label-position="top">
          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item>
                <template #label>砂率 β<sub>s</sub></template>
                <el-input-number
                  :model-value="store.sandRatioInput ?? undefined"
                  @update:model-value="v => store.sandRatioInput = v ?? null"
                  :min="0" :max="100" :step="1" :precision="1"
                  placeholder="输入砂率"
                  style="width:100%"
                >
                  <template #suffix><span class="unit-suffix">%</span></template>
                </el-input-number>
                <div class="input-hint">参考范围 {{ getRange() }} %<template v-if="store.importedValueText('sand_ratio', ' %', 2)">，{{ store.importedValueText('sand_ratio', ' %', 2) }}</template></div>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>

        <el-alert
          v-if="store.sandRatioConfirmed"
          :title="`已确认砂率 ${store.sandRatioInput} %，已自动填入骨料计算`"
          type="success"
          :closable="false"
          show-icon
          style="margin-bottom:10px"
        />

        <el-alert type="info" :closable="false">
          <template #title>计算公式说明</template>
          <template #default>
            <Formula latex="\beta_s = \frac{m_s}{\,m_s + m_g\,} \times 100\%" />
          </template>
        </el-alert>

        <div class="footer-actions">
          <el-button type="primary" :disabled="!store.sandRatioInput" @click="emit('next-step')">
            下一步
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sr-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 12px;
  font-size: 13px;
}
.sr-table th, .sr-table td {
  border: 1px solid #dde4f0;
  padding: 9px 14px;
  text-align: center;
}
.sr-table thead th {
  background: linear-gradient(135deg, #1e3c72, #2a5298);
  color: #fff;
  cursor: pointer;
  user-select: none;
  font-weight: 700;
}
.sr-table thead th:hover:not(:first-child),
.sr-table thead th.head-selected {
  background: linear-gradient(135deg, #2a5298, #4a73b8);
}
.row-label-cell {
  font-weight: 700;
  cursor: pointer;
  color: #333;
  user-select: none;
}
.row-label-cell:hover, .row-label-cell.row-selected {
  background: #e8f5e9 !important;
  color: #2e7d32;
}
.data-cell { transition: background 0.15s; }
.sr-table tbody tr:nth-child(even) td { background: #f8faff; }
</style>
