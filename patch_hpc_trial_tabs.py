import os

BASE = r'd:\Code\shuini_calculator\frontend\src\components\hpc-trial'

# ---- HpcTrialCorrectionTab ----
correction_tpl = '''<template>
  <div>
    <el-alert
      v-if="!hasData"
      title="请先在"配比计算 → 高性能混凝土"中完成配合比计算，之后再回到本页进行试配调整。"
      type="warning"
      show-icon
      :closable="false"
      style="margin-bottom: 16px"
    />

    <template v-else>
      <!-- 调整配合比 -->
      <div class="cs-section">
        <div class="cs-section-head">
          <el-icon><Edit /></el-icon>
          调整配合比（来自强度实验调整结果）
        </div>
        <div class="cs-section-body">
          <p style="font-size: 12px; color: #909399; margin: 0 0 10px">
            本页直接承接前一步根据推荐水胶比生成的最终配合比结果，并继续进行表观密度校正与实验室配合比确认。
          </p>
          <HpcTrialDataTable :columns="materialColumns" :rows="adaptResultRows" variant="trial-adjust" />
        </div>
      </div>

      <!-- 表观密度校正 -->
      <div class="cs-section">
        <div class="cs-section-head">
          <el-icon><Odometer /></el-icon>
          表观密度校正
        </div>
        <div class="cs-section-body">
          <p style="font-size: 12px; color: #909399; margin: 0 0 12px">
            测定拌合物表观密度后，按校正系数 δ = ρ<sub>c,t</sub> / ρ<sub>c,c</sub> 修正实验室配合比，各组分比例保持不变。
          </p>
          <el-form label-position="top" size="default">
            <el-row :gutter="20">
              <el-col :span="6">
                <el-form-item>
                  <template #label>实测表观密度 ρ<sub>c,t</sub></template>
                  <el-input-number v-model="measuredDensity" :min="1000" :max="3000" :step="1" :precision="0" style="width: 100%">
                    <template #suffix><span class="unit-suffix">kg/m³</span></template>
                  </el-input-number>
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item>
                  <template #label>计算表观密度 ρ<sub>c,c</sub></template>
                  <el-input :value="calculatedDensity ? calculatedDensity.toFixed(2) : \'—\'" readonly>
                    <template #suffix><span class="unit-suffix">kg/m³</span></template>
                  </el-input>
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item>
                  <template #label>校正系数 δ</template>
                  <el-input :value="densityCorrectionFactor ? densityCorrectionFactor.toFixed(6) : \'—\'" readonly />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </div>
      </div>

      <!-- 实验室配合比 -->
      <div class="cs-section">
        <div class="cs-section-head">
          <el-icon><DocumentChecked /></el-icon>
          实验室配合比
        </div>
        <div class="cs-section-body">
          <p style="font-size: 12px; color: #909399; margin: 0 0 10px">
            调整配合比各材料用量 × δ，保持目标水胶比不变。
          </p>
          <div style="display: flex; gap: 8px; margin-bottom: 14px">
            <el-button size="small" type="default" @click="resetCorrection">
              <el-icon><RefreshLeft /></el-icon>
              重置校正
            </el-button>
          </div>
          <HpcTrialDataTable :columns="materialColumns" :rows="labMixRows" variant="lab-mix" />

          <div v-if="densityCorrectionFactor" class="total-card">
            <span class="total-label">实验室配合比每方合计</span>
            <span class="total-val">{{ labMix.total ? labMix.total.toFixed(2) + \' kg/m³\' : \'—\' }}</span>
          </div>

          <el-alert type="info" :closable="false" style="margin-top: 14px">
            <template #title>校正说明</template>
            <template #default>
              <p style="margin: 0; line-height: 1.8; font-size: 12px">
                当拌合物表观密度实测值与计算值偏差较大时，应按校正系数 δ 对实验室配合比进行统一放大或缩小，
                以保证后续试验配比与实测状态一致。
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

# ---- HpcTrialStrengthTab ----
strength_tpl = '''<template>
  <div>
    <el-alert
      v-if="!hasData"
      title="请先在"配比计算 → 高性能混凝土"中完成配合比计算。"
      type="warning"
      show-icon
      :closable="false"
      style="margin-bottom: 16px"
    />

    <template v-else>
      <div class="cs-section">
        <div class="cs-section-head">
          <el-icon><List /></el-icon>
          基准与三组强度实验配合比
        </div>
        <div class="cs-section-body">
          <HpcTrialStrengthMixSection
            :material-columns="materialColumns"
            :mix-columns="mixColumns"
            :base-wb="baseWb"
            :base-bs="baseBs"
            :base-binder="workabilityResult.mb"
            :base-material-rows="baseMaterialRows"
            :strength-mix-table-rows="strengthMixTableRows"
          />
        </div>
      </div>

      <div class="cs-section">
        <div class="cs-section-head">
          <el-icon><Edit /></el-icon>
          强度试验参数
        </div>
        <div class="cs-section-body">
          <HpcTrialStrengthControlSection
            v-model:delta-wb="deltaWb"
            v-model:delta-bs="deltaBs"
            v-model:strength0="strength0"
            v-model:strength-p="strengthP"
            v-model:strength-n="strengthN"
            v-model:s-target-strength="sTargetStrength"
          />
        </div>
      </div>

      <div class="cs-section">
        <div class="cs-section-head">
          <el-icon><TrendCharts /></el-icon>
          强度回归分析
        </div>
        <div class="cs-section-body">
          <HpcTrialStrengthAnalysisSection
            :strength-relation-rows="strengthRelationRows"
            :strength-regression="strengthRegression"
            :chart-data="chartData"
            :delta-wb="deltaWb"
            :delta-bs="deltaBs"
            :s-target-strength="sTargetStrength"
            :base-wb="baseWb"
          />
        </div>
      </div>

      <div style="margin-top: 12px">
        <el-button type="default" @click="resetStrength">
          <el-icon><RefreshLeft /></el-icon>
          重置强度实验
        </el-button>
      </div>
    </template>
  </div>
</template>
'''

def patch_file_script_and_template(filepath, new_template_and_style):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add CSS import if not present
    if 'calc-tabs.css' not in content:
        lines = content.split('\n')
        last_import_idx = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') and '</script>' not in line:
                last_import_idx = i
        if last_import_idx >= 0:
            lines.insert(last_import_idx + 1, "import '../../style/calc-tabs.css'")
            content = '\n'.join(lines)
    
    # Replace from <template> to end
    tpl_idx = content.index('<template>')
    result = content[:tpl_idx] + new_template_and_style
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(result)
    print(f'Updated {os.path.basename(filepath)}: {result.count(chr(10))} lines')

patch_file_script_and_template(
    os.path.join(BASE, 'HpcTrialCorrectionTab.vue'),
    correction_tpl
)
patch_file_script_and_template(
    os.path.join(BASE, 'HpcTrialStrengthTab.vue'),
    strength_tpl
)
print('Done HPC trial tabs (Correction + Strength)')
