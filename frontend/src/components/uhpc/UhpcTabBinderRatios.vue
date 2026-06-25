<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import Formula from '../Formula.vue'
import { saveRecord } from '../../api/records'
import { UHPC_INPUT_PLACEHOLDERS, useUhpcStore } from '../../stores/uhpcStore'
import '../../style/calc-tabs.css'

const store = useUhpcStore()
const route = useRoute()
const saveVisible = ref(false)
const saveName = ref('')
const saving = ref(false)

function parseProjectId(value: unknown): number | null {
  const raw = Array.isArray(value) ? value[0] : value
  const projectId = Number(raw)
  return Number.isInteger(projectId) && projectId > 0 ? projectId : null
}

const currentProjectId = computed(() => (
  parseProjectId(route.query.project_id)
  ?? store.currentRecordProjectId
  ?? store.uhpcSelectedProjectId
))

const canUpdateCurrentRecord = computed(() => (
  store.currentRecordId !== null
  && !!store.currentRecordName.trim()
  && store.currentRecordProjectId === currentProjectId.value
))

const saveButtonText = computed(() => canUpdateCurrentRecord.value ? '保存修改' : '保存配比记录')

const flyAshAccumulationNote = '注：对 C130 为 6~10 μm，对 C150 为 2~7 μm。当粉煤灰 28d 活性 > 85% 时，可取偏大值；当粉煤灰 28d 活性 < 80% 时，可取偏小值。'
const microBeadRatioNote = '注：取 0.4~0.6。当微珠 28d 活性 > 105% 时，可取偏大值；当微珠 28d 活性 ≤ 95% 时，可取偏小值。'
const microPowderCoefficientNote = '注：对 C130 取 0.4~0.6，对 C150 取 0.8~1.0；当硅灰的活性 ≤ 110% 时，可取偏大值；当硅灰的活性 > 115% 时，可取偏小值。'

const ratioRows = computed(() => ([
  {
    label: '水泥',
    volume: store.binderVolumeRatios.cement,
    initial: store.binderMassRatios.initial.cement,
    corrected: store.binderMassRatios.corrected.cement,
  },
  {
    label: '粉煤灰',
    volume: store.binderVolumeRatios.flyAsh,
    initial: store.binderMassRatios.initial.flyAsh,
    corrected: store.binderMassRatios.corrected.flyAsh,
  },
  {
    label: '微珠',
    volume: store.binderVolumeRatios.microBead,
    initial: store.binderMassRatios.initial.microBead,
    corrected: store.binderMassRatios.corrected.microBead,
  },
  {
    label: '硅灰',
    volume: store.binderVolumeRatios.silicaFume,
    initial: store.binderMassRatios.initial.silicaFume,
    corrected: store.binderMassRatios.corrected.silicaFume,
  },
]))

const materialRows = computed(() => ([
  { label: '胶凝材料 m<sub>b</sub>', value: store.materialMasses.binder, unit: 'kg/m³' },
  { label: '水泥 m<sub>c</sub>', value: store.materialMasses.cement, unit: 'kg/m³' },
  { label: '粉煤灰 m<sub>fa</sub>', value: store.materialMasses.flyAsh, unit: 'kg/m³' },
  { label: '微珠 m<sub>cm</sub>', value: store.materialMasses.microBead, unit: 'kg/m³' },
  { label: '硅灰 m<sub>sf</sub>', value: store.materialMasses.silicaFume, unit: 'kg/m³' },
  { label: '砂 m<sub>s</sub>', value: store.materialMasses.sand, unit: 'kg/m³' },
  { label: '钢纤维 m<sub>f</sub>', value: store.materialMasses.steelFiber, unit: 'kg/m³' },
  { label: '水 m<sub>w</sub>', value: store.materialMasses.water, unit: 'kg/m³' },
  { label: '外加剂 m<sub>a</sub>', value: store.materialMasses.admixture, unit: 'kg/m³' },
]))

function fmt(value: number | null, digits = 2): string {
  return value !== null ? value.toFixed(digits) : '—'
}

async function persistRecord(name: string) {
  const finalName = name.trim()
  if (!finalName) {
    ElMessage.warning('请输入配比名称')
    return
  }

  if (currentProjectId.value === null) {
    ElMessage.warning('当前配比未关联项目，无法保存')
    return
  }

  await store.calcMix()
  if (!store.hasResults) {
    ElMessage.warning('请先完成参数填写并得到有效的 UHPC 计算结果')
    return
  }

  saving.value = true
  try {
    const result = await saveRecord(store.buildRecordPayload(
      finalName,
      currentProjectId.value,
      canUpdateCurrentRecord.value ? store.currentRecordId : null,
    ))
    const snapshot = store.buildDesignSnapshot()
    store.markRecordSaved(result.id, finalName, currentProjectId.value)
    store.setCurrentDesignData(snapshot)
    saveVisible.value = false
    ElMessage.success(canUpdateCurrentRecord.value ? 'UHPC 配比已更新' : 'UHPC 配比已保存')
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : 'UHPC 配比保存失败')
  } finally {
    saving.value = false
  }
}

async function handleFinish() {
  await store.calcMix()
  if (!store.hasResults) {
    return
  }

  if (canUpdateCurrentRecord.value) {
    await persistRecord(store.currentRecordName)
    return
  }

  saveName.value = store.currentRecordName || 'UHPC 配比记录'
  saveVisible.value = true
}
</script>

<template>
  <div>
    <el-alert
      v-if="store.strengthGrade === null || store.waterBinderRatio === null || store.sandBinderRatio === null || store.steelFiberVolumeRatio === null || store.admixtureRatio === null"
      title="请先完成前 3 个页签的基础参数录入。"
      type="warning"
      :closable="false"
      style="margin-bottom:16px"
    />

    <!-- 级配与比例参数 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><SetUp /></el-icon>
        级配与比例参数
      </div>
      <div class="cs-section-body">
        <el-form label-position="top" class="binder-form">
          <section class="binder-form-section">
            <div class="binder-form-section__title">级配控制参数</div>
            <div class="binder-form-grid binder-form-grid--three">
              <div class="binder-form-field">
                <el-form-item>
                  <template #label>体系最大粒径 D<sub>L</sub></template>
                  <el-input-number :model-value="store.maxParticleSize ?? undefined" @update:model-value="value => store.maxParticleSize = value ?? null" :min="1" :step="1" style="width:100%">
                    <template #suffix><span class="unit-suffix">μm</span></template>
                  </el-input-number>
                </el-form-item>
                <div class="field-hint">参考值：80 μm</div>
                <div v-if="store.importedValueText('max_particle_size', ' μm', 2)" class="field-hint">{{ store.importedValueText('max_particle_size', ' μm', 2) }}</div>
              </div>
              <div class="binder-form-field">
                <el-form-item>
                  <template #label>体系最小粒径 D<sub>S</sub></template>
                  <el-input-number :model-value="store.minParticleSize ?? undefined" @update:model-value="value => store.minParticleSize = value ?? null" :min="0.1" :step="0.1" :precision="2" style="width:100%">
                    <template #suffix><span class="unit-suffix">μm</span></template>
                  </el-input-number>
                </el-form-item>
                <div class="field-hint">参考值：1 μm</div>
                <div v-if="store.importedValueText('min_particle_size', ' μm', 2)" class="field-hint">{{ store.importedValueText('min_particle_size', ' μm', 2) }}</div>
              </div>
              <div class="binder-form-field">
                <el-form-item>
                  <template #label>粒径分布指数 q</template>
                  <el-input-number :model-value="store.distributionIndex ?? undefined" @update:model-value="value => store.distributionIndex = value ?? null" :min="0.01" :step="0.01" :precision="3" style="width:100%" />
                </el-form-item>
                <div class="field-hint">参考值：0.22</div>
                <div v-if="store.importedValueText('distribution_index', '', 3)" class="field-hint">{{ store.importedValueText('distribution_index', '', 3) }}</div>
              </div>
            </div>
          </section>

          <section class="binder-form-section">
            <div class="binder-form-section__title">粉体粒径参数</div>
            <div class="binder-form-grid binder-form-grid--three">
              <div class="binder-form-field">
                <el-form-item>
                  <template #label>粉煤灰峰值粒径 D<sub>pfa</sub></template>
                  <el-input-number :model-value="store.flyAshPeakSize ?? undefined" @update:model-value="value => store.flyAshPeakSize = value ?? null" :min="0.1" :step="0.5" :precision="2" style="width:100%">
                    <template #suffix><span class="unit-suffix">μm</span></template>
                  </el-input-number>
                </el-form-item>
                <div class="field-hint">参考值：18 μm</div>
                <div v-if="store.importedValueText('fly_ash_peak_size', ' μm', 2)" class="field-hint">{{ store.importedValueText('fly_ash_peak_size', ' μm', 2) }}</div>
              </div>
              <div class="binder-form-field">
                <el-form-item>
                  <template #label>粉煤灰堆积粒径 I<sub>fa</sub></template>
                  <el-input-number :model-value="store.flyAshAccumulationSize ?? undefined" @update:model-value="value => store.flyAshAccumulationSize = value ?? null" :min="0.1" :step="0.5" :precision="2" style="width:100%">
                    <template #suffix><span class="unit-suffix">μm</span></template>
                  </el-input-number>
                </el-form-item>
                <div class="field-hint">参考值：8 μm</div>
                <div v-if="store.importedValueText('fly_ash_accumulation_size', ' μm', 2)" class="field-hint">{{ store.importedValueText('fly_ash_accumulation_size', ' μm', 2) }}</div>
                <div class="field-note">{{ flyAshAccumulationNote }}</div>
              </div>
              <div class="binder-form-field">
                <el-form-item>
                  <template #label>微珠峰值粒径 D<sub>pm</sub></template>
                  <el-input-number :model-value="store.microBeadPeakSize ?? undefined" @update:model-value="value => store.microBeadPeakSize = value ?? null" :min="0.1" :step="0.1" :precision="2" style="width:100%">
                    <template #suffix><span class="unit-suffix">μm</span></template>
                  </el-input-number>
                </el-form-item>
                <div class="field-hint">参考值：4 μm</div>
                <div v-if="store.importedValueText('micro_bead_peak_size', ' μm', 2)" class="field-hint">{{ store.importedValueText('micro_bead_peak_size', ' μm', 2) }}</div>
              </div>
            </div>
          </section>

          <section class="binder-form-section">
            <div class="binder-form-section__title">比例与质量参数</div>
            <div class="binder-form-grid binder-form-grid--three">
              <div class="binder-form-field">
                <el-form-item>
                  <template #label>微珠占硅灰、微粉比例 I<sub>ce</sub></template>
                  <el-input-number :model-value="store.microBeadSilicaFumeRatio ?? undefined" @update:model-value="value => store.microBeadSilicaFumeRatio = value ?? null" :min="0.1" :max="0.9" :step="0.05" :precision="2" style="width:100%" />
                </el-form-item>
                <div class="field-hint">参考值：0.50</div>
                <div v-if="store.importedValueText('micro_bead_silica_fume_ratio', '', 2)" class="field-hint">{{ store.importedValueText('micro_bead_silica_fume_ratio', '', 2) }}</div>
                <div class="field-note">{{ microBeadRatioNote }}</div>
              </div>
              <div class="binder-form-field">
                <el-form-item>
                  <template #label>微粉系数 I<sub>m</sub></template>
                  <el-input-number :model-value="store.microPowderCoefficient ?? undefined" @update:model-value="value => store.microPowderCoefficient = value ?? null" :min="0.1" :max="2" :step="0.05" :precision="2" style="width:100%" />
                </el-form-item>
                <div class="field-hint">参考值：0.55</div>
                <div v-if="store.importedValueText('micro_powder_coefficient', '', 2)" class="field-hint">{{ store.importedValueText('micro_powder_coefficient', '', 2) }}</div>
                <div class="field-note">{{ microPowderCoefficientNote }}</div>
              </div>
              <div class="binder-form-field">
                <el-form-item>
                  <template #label>假定拌合物质量 m<sub>cp</sub></template>
                  <el-input-number :model-value="store.assumedMixMass ?? undefined" @update:model-value="value => store.assumedMixMass = value ?? null" :min="1000" :step="50" :precision="0" style="width:100%">
                    <template #suffix><span class="unit-suffix">kg/m³</span></template>
                  </el-input-number>
                </el-form-item>
                <div class="field-hint">参考值：2500 kg/m³</div>
                <div v-if="store.importedValueText('assumed_mix_mass', ' kg/m³', 0)" class="field-hint">{{ store.importedValueText('assumed_mix_mass', ' kg/m³', 0) }}</div>
              </div>
            </div>
          </section>

          <section class="binder-form-section">
            <div class="binder-form-section__title">材料密度</div>
            <div class="binder-form-grid binder-form-grid--four">
              <div class="binder-form-field">
                <el-form-item>
                  <template #label>水泥密度 ρ<sub>c</sub></template>
                  <el-input-number :model-value="store.cementDensity ?? undefined" @update:model-value="value => store.cementDensity = value ?? null" :min="1" :step="10" :precision="0" style="width:100%">
                    <template #suffix><span class="unit-suffix">kg/m³</span></template>
                  </el-input-number>
                </el-form-item>
                <div class="field-hint">参考值：3100 kg/m³</div>
                <div v-if="store.importedValueText('cement_density', ' kg/m³', 0)" class="field-hint">{{ store.importedValueText('cement_density', ' kg/m³', 0) }}</div>
              </div>
              <div class="binder-form-field">
                <el-form-item>
                  <template #label>粉煤灰密度 ρ<sub>1</sub></template>
                  <el-input-number :model-value="store.flyAshDensity ?? undefined" @update:model-value="value => store.flyAshDensity = value ?? null" :min="1" :step="10" :precision="0" style="width:100%">
                    <template #suffix><span class="unit-suffix">kg/m³</span></template>
                  </el-input-number>
                </el-form-item>
                <div class="field-hint">参考值：2200 kg/m³</div>
                <div v-if="store.importedValueText('fly_ash_density', ' kg/m³', 0)" class="field-hint">{{ store.importedValueText('fly_ash_density', ' kg/m³', 0) }}</div>
              </div>
              <div class="binder-form-field">
                <el-form-item>
                  <template #label>微珠密度 ρ<sub>3</sub></template>
                  <el-input-number :model-value="store.microBeadDensity ?? undefined" @update:model-value="value => store.microBeadDensity = value ?? null" :min="1" :step="10" :precision="0" style="width:100%">
                    <template #suffix><span class="unit-suffix">kg/m³</span></template>
                  </el-input-number>
                </el-form-item>
                <div class="field-hint">参考值：2100 kg/m³</div>
                <div v-if="store.importedValueText('micro_bead_density', ' kg/m³', 0)" class="field-hint">{{ store.importedValueText('micro_bead_density', ' kg/m³', 0) }}</div>
              </div>
              <div class="binder-form-field">
                <el-form-item>
                  <template #label>硅灰密度 ρ<sub>4</sub></template>
                  <el-input-number :model-value="store.silicaFumeDensity ?? undefined" @update:model-value="value => store.silicaFumeDensity = value ?? null" :min="1" :step="10" :precision="0" style="width:100%">
                    <template #suffix><span class="unit-suffix">kg/m³</span></template>
                  </el-input-number>
                </el-form-item>
                <div class="field-hint">参考值：2400 kg/m³</div>
                <div v-if="store.importedValueText('silica_fume_density', ' kg/m³', 0)" class="field-hint">{{ store.importedValueText('silica_fume_density', ' kg/m³', 0) }}</div>
              </div>
            </div>
          </section>
        </el-form>
      </div>
    </div>

    <!-- 计算结果 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><PieChart /></el-icon>
        计算结果
      </div>
      <div class="cs-section-body">
        <el-alert v-if="store.error" :title="store.error" type="error" :closable="false" show-icon style="margin-bottom:16px" />

        <template v-if="store.hasResults">
          <p style="font-size:12px;color:#909399;margin-bottom:8px">胶凝材料比例</p>
          <el-table :data="ratioRows" size="small" border style="margin-bottom:16px">
            <el-table-column prop="label" label="材料" min-width="120" />
            <el-table-column label="体积比例 V¹ (%)" min-width="120">
              <template #default="{ row }">{{ fmt(row.volume) }}</template>
            </el-table-column>
            <el-table-column label="初始质量比例 M¹ (%)" min-width="140">
              <template #default="{ row }">{{ fmt(row.initial) }}</template>
            </el-table-column>
            <el-table-column label="修正质量比例 M² (%)" min-width="140">
              <template #default="{ row }">{{ fmt(row.corrected) }}</template>
            </el-table-column>
          </el-table>

          <p style="font-size:12px;color:#909399;margin-bottom:8px">计算配合比</p>
          <div class="mass-grid">
            <div v-for="row in materialRows" :key="row.label" class="mass-card">
              <div class="mass-card__label" v-html="row.label"></div>
              <div class="mass-card__value">{{ fmt(row.value) }}</div>
              <div class="mass-card__unit">{{ row.unit }}</div>
            </div>
          </div>

          <div class="total-card">
            <span class="total-card__label">每方材料合计</span>
            <span class="total-card__value">{{ fmt(store.materialMasses.total) }} kg/m³</span>
          </div>
        </template>

        <el-alert type="info" :closable="false" style="margin-top:16px">
          <template #title>核心公式</template>
          <template #default>
            <Formula latex="V_D = \frac{D^q - D_S^q}{D_L^q - D_S^q} \times 100\%" style="margin-bottom:8px" />
            <Formula latex="m_b + m_s + m_w + m_a + m_f = m_{cp}" style="margin-bottom:8px" />
            <Formula latex="m_s = m_b \times (S/B),\; m_w = m_b \times (W/B),\; m_a = m_b \times \alpha" />
          </template>
        </el-alert>

        <div class="footer-actions">
          <el-button type="primary" :loading="store.loading || saving" :disabled="!store.hasResults" @click="handleFinish">
            {{ saveButtonText }}
            <el-icon><FolderAdd /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <el-dialog v-model="saveVisible" title="保存 UHPC 配比记录" width="420px">
      <el-form label-width="96px">
        <el-form-item label="记录名称">
          <el-input v-model="saveName" maxlength="100" placeholder="请输入 UHPC 配比记录名称" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="saveVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="persistRecord(saveName)">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.binder-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.binder-form-section {
  padding: 16px;
  border: 1px solid #eef3fb;
  border-radius: 10px;
  background: #fafcff;
}

.binder-form-section__title {
  margin-bottom: 12px;
  color: #52606d;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.binder-form-grid {
  display: grid;
  gap: 16px;
}

.binder-form-grid--three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.binder-form-grid--four {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.binder-form-field {
  min-width: 0;
}

.binder-form-field :deep(.el-form-item) {
  margin-bottom: 0;
}

.field-hint {
  margin-top: 6px;
  color: #a8abb2;
  font-size: 11px;
  line-height: 1.5;
}

.field-note {
  margin-top: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid #e2eaf5;
  background: #f5f8fc;
  color: #637381;
  font-size: 11px;
  line-height: 1.6;
}

.mass-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.mass-card {
  padding: 12px;
  border-radius: 10px;
  background: linear-gradient(180deg, #ffffff, #f4f7fb);
  border: 1px solid #dbe5f1;
}

.mass-card__label {
  color: #52606d;
  font-size: 12px;
}

.mass-card__value {
  margin-top: 6px;
  color: #1e3c72;
  font-size: 20px;
  font-weight: 800;
}

.mass-card__unit {
  margin-top: 2px;
  color: #7b8794;
  font-size: 11px;
}

.total-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  border-radius: 10px;
  background: linear-gradient(135deg, #0f274b, #2a5298);
  color: #fff;
}

.total-card__label {
  font-size: 14px;
  font-weight: 600;
}

.total-card__value {
  font-size: 22px;
  font-weight: 800;
}

@media (max-width: 1200px) {
  .binder-form-grid--three,
  .binder-form-grid--four {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .mass-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>