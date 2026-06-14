f = open(r'd:\Code\shuini_calculator\frontend\src\components\hpc-trial\HpcTrialWorkabilityTab.vue', 'r', encoding='utf-8')
content = f.read()
f.close()

# Add CSS import
if 'calc-tabs.css' not in content:
    lines = content.split('\n')
    last_import_idx = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('import ') and '</script>' not in line:
            last_import_idx = i
    if last_import_idx >= 0:
        lines.insert(last_import_idx + 1, "import '../../style/calc-tabs.css'")
        content = '\n'.join(lines)

tpl_idx = content.index('<template>')
script_part = content[:tpl_idx]

new_template = '''<template>
  <div>
    <el-alert
      v-if="!hasData"
      title="请先在"配比计算 → 高性能混凝土"中完成配合比计算，之后再回到本页进行工作性实验。"
      type="warning"
      show-icon
      :closable="false"
      style="margin-bottom: 16px"
    />

    <template v-else>
      <!-- 计算配合比 -->
      <div class="cs-section">
        <div class="cs-section-head">
          <el-icon><List /></el-icon>
          计算配合比（每方用量）
        </div>
        <div class="cs-section-body">
          <HpcTrialDataTable :columns="materialColumns" :rows="baseMaterialRows" />
        </div>
      </div>

      <!-- 调整变量 -->
      <div class="cs-section">
        <div class="cs-section-head">
          <el-icon><Setting /></el-icon>
          基础调整变量
        </div>
        <div class="cs-section-body">
          <p class="trial-adjust-note">
            水胶比 W/B 固定为 {{ fmt(wbVal, 4) }}。下列三个基准量不可直接修改，通过右侧增减量重算工作性试拌配合比。
          </p>
          <el-form label-position="top" size="default">
            <el-row :gutter="20">
              <el-col :span="8">
                <el-form-item>
                  <template #label>胶材用量 m<sub>b</sub></template>
                  <div class="trial-adjust-control">
                    <el-input :model-value="fmt(mbVal)" readonly class="trial-readonly-input">
                      <template #suffix><span class="unit-suffix">kg/m³</span></template>
                    </el-input>
                    <el-input-number
                      v-model="workabilityBinderDelta"
                      :step="5"
                      :precision="2"
                      :min="binderDeltaMin"
                      style="width: 100%"
                    >
                      <template #suffix><span class="unit-suffix">Δkg</span></template>
                    </el-input-number>
                  </div>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item>
                  <template #label>砂率 β<sub>s</sub></template>
                  <div class="trial-adjust-control">
                    <el-input :model-value="fmt(sandRatioVal)" readonly class="trial-readonly-input">
                      <template #suffix><span class="unit-suffix">%</span></template>
                    </el-input>
                    <el-input-number
                      v-model="workabilitySandRatioDelta"
                      :step="0.5"
                      :precision="2"
                      :min="sandRatioDeltaMin"
                      :max="sandRatioDeltaMax"
                      style="width: 100%"
                    >
                      <template #suffix><span class="unit-suffix">Δ%</span></template>
                    </el-input-number>
                  </div>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item>
                  <template #label>外加剂掺量 α</template>
                  <div class="trial-adjust-control">
                    <el-input :model-value="fmt(alphaVal)" readonly class="trial-readonly-input">
                      <template #suffix><span class="unit-suffix">%</span></template>
                    </el-input>
                    <el-input-number
                      v-model="workabilityAlphaDelta"
                      :step="0.05"
                      :precision="2"
                      :min="alphaDeltaMin"
                      style="width: 100%"
                    >
                      <template #suffix><span class="unit-suffix">Δ%</span></template>
                    </el-input-number>
                  </div>
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </div>
      </div>

      <!-- 试拌配合比 -->
      <div class="cs-section">
        <div class="cs-section-head">
          <el-icon><Grid /></el-icon>
          试拌配合比
        </div>
        <div class="cs-section-body">
          <p style="font-size: 12px; color: #909399; margin: 0 0 10px">调整后试拌配合比与试拌用量</p>
          <div class="materials-table-wrap">
            <el-table
              :data="mergedMixRows"
              border
              size="small"
              table-layout="fixed"
              class="materials-table materials-table--workability-merged"
              :cell-class-name="resolveMergedCellClassName"
            >
              <el-table-column prop="trialVolume" label="试拌体积" :min-width="120" align="center" fixed="left">
                <template #default="{ row }">
                  <div v-if="row.rowKey === 'trial-batch'" class="trial-volume-cell">
                    <el-input-number
                      v-model="batchVolume"
                      :min="1"
                      :max="100"
                      :step="5"
                      style="width: 100%"
                    >
                      <template #suffix><span class="unit-suffix">L</span></template>
                    </el-input-number>
                  </div>
                  <div v-else class="trial-cell">
                    <span class="trial-val">{{ getCellText(row.trialVolume) }}</span>
                    <span v-if="getCellUnit(row.trialVolume)" class="trial-unit">{{ getCellUnit(row.trialVolume) }}</span>
                  </div>
                </template>
              </el-table-column>

              <el-table-column
                v-for="column in materialColumns"
                :key="column.key"
                :prop="column.key"
                :label="column.label"
                :min-width="82"
                align="center"
              >
                <template #default="{ row }">
                  <div v-if="getCellUnit(row[column.key])" class="trial-cell">
                    <span class="trial-val">{{ getCellText(row[column.key]) }}</span>
                    <span class="trial-unit">{{ getCellUnit(row[column.key]) }}</span>
                  </div>
                  <span v-else class="trial-table-text">{{ getCellText(row[column.key]) }}</span>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div class="formula-row" style="margin-top: 6px">
            <span class="formula-label">固定 W/B：</span>
            <span class="formula-val">{{ fmt(workabilityResult.wb, 4) }}</span>
            <span class="formula-label" style="margin-left: 20px">调整后 m<sub>b</sub>：</span>
            <span class="formula-val" :class="{ changed: workabilityBinderDelta !== 0 }">{{ fmt(workabilityResult.mb) }} kg/m³</span>
            <span class="formula-label" style="margin-left: 20px">调整后 β<sub>s</sub>：</span>
            <span class="formula-val" :class="{ changed: workabilitySandRatioDelta !== 0 }">{{ fmt(workabilityResult.bs) }} %</span>
            <span class="formula-label" style="margin-left: 20px">调整后 α：</span>
            <span class="formula-val" :class="{ changed: workabilityAlphaDelta !== 0 }">{{ fmt(workabilityResult.alpha) }} %</span>
          </div>
        </div>
      </div>

      <!-- 工作性评价 -->
      <div class="cs-section">
        <div class="cs-section-head">
          <el-icon><DataAnalysis /></el-icon>
          工作性评价
        </div>
        <div class="cs-section-body">
          <p style="font-size: 12px; color: #909399; margin: 0 0 10px">
            根据上方调整后的配合比完成试拌，并记录坍落度、扩展度、粘聚性、保水性以及是否满足目标工作性要求。
          </p>
          <el-form label-position="top" size="default">
            <el-row :gutter="20">
              <el-col :span="6">
                <el-form-item>
                  <template #label>实测坍落度</template>
                  <el-input-number
                    v-model="slumpMeasured"
                    :min="0"
                    :max="300"
                    :step="5"
                    placeholder="如 180"
                    style="width: 100%"
                  >
                    <template #suffix><span class="unit-suffix">mm</span></template>
                  </el-input-number>
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item>
                  <template #label>实测扩展度</template>
                  <el-input-number
                    v-model="spreadMeasured"
                    :min="0"
                    :max="900"
                    :step="5"
                    placeholder="如 650"
                    style="width: 100%"
                  >
                    <template #suffix><span class="unit-suffix">mm</span></template>
                  </el-input-number>
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>

          <el-form label-position="top" size="default">
            <el-row :gutter="20">
              <el-col :span="24">
                <el-form-item>
                  <template #label>工作性描述（粘聚性、保水性、离析泌水等）</template>
                  <el-input
                    v-model="workabilityNote"
                    type="textarea"
                    :rows="2"
                    placeholder="如：拌合物粘聚性良好，无离析泌水现象..."
                  />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="24">
                <div class="trial-workability-actions">
                  <el-button type="default" @click="resetWorkability">
                    <el-icon><RefreshLeft /></el-icon>
                    重置工作性
                  </el-button>
                  <div class="trial-workability-evaluation">
                    <span class="trial-workability-evaluation__label">工作性评价</span>
                    <el-tag :type="workabilityEvaluation.tagType" size="small">{{ workabilityEvaluation.label }}</el-tag>
                    <span class="trial-workability-evaluation__detail">
                      {{ selectedWorkabilityReference ? workabilityEvaluation.detail : '请先在"骨料用量"中选择 Vg 参考范围。' }}
                    </span>
                  </div>
                </div>
              </el-col>
            </el-row>
          </el-form>

          <div class="total-card">
            <span class="total-label">调整后每方合计</span>
            <span class="total-val">{{ workabilityResult.total ? workabilityResult.total.toFixed(2) + ' kg/m³' : '—' }}</span>
          </div>

          <el-alert type="info" :closable="false" style="margin-top: 12px">
            <template #title>工作性实验说明</template>
            <template #default>
              <p style="margin: 0; line-height: 1.8; font-size: 12px">
                先以设计配合比为基准，保持水胶比不变，通过调整胶材用量、砂率和外加剂掺量重算每方配合比，
                其中调整砂率时保持粗骨料与细骨料总量不变，按目标砂率重新分配粗细骨料，
                再按试拌体积换算各材料试拌用量。确认工作性满足目标后，点击页面下方"下一步"即可进入强度实验。
              </p>
            </template>
          </el-alert>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.total-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 14px;
  padding: 14px 18px;
  border-radius: 10px;
  background: linear-gradient(135deg, #1e3c72, #2a5298);
  color: #fff;
}
.total-label { font-size: 14px; font-weight: 600; }
.total-val { font-size: 22px; font-weight: 800; }
</style>
'''

result = script_part + new_template
open(r'd:\Code\shuini_calculator\frontend\src\components\hpc-trial\HpcTrialWorkabilityTab.vue', 'w', encoding='utf-8').write(result)
print('Done HpcTrialWorkabilityTab:', result.count('\n'), 'lines')
