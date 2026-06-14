import os

BASE = r'd:\Code\shuini_calculator\frontend\src\components\uhpc'

# --- UhpcTabWaterBinder ---
wb_tpl = '''<template>
  <div>
    <!-- 强度等级与参考 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><DataAnalysis /></el-icon>
        强度等级与参考
      </div>
      <div class="cs-section-body">
        <el-form label-position="top">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item>
                <template #label>强度等级 f<sub>cu,k</sub></template>
                <el-input-number
                  :model-value="store.strengthGrade ?? undefined"
                  @update:model-value="value => store.strengthGrade = value ?? null"
                  :min="130" :step="20" :precision="0"
                  :placeholder="UHPC_INPUT_PLACEHOLDERS.strengthGrade"
                  style="width:100%"
                >
                  <template #suffix><span class="unit-suffix">MPa</span></template>
                </el-input-number>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item>
                <template #label>配制强度 f<sub>cu,0</sub></template>
                <el-input :model-value="designStrength !== null ? designStrength.toFixed(2) : ''" readonly class="computed-input">
                  <template #suffix><span class="unit-suffix">MPa</span></template>
                </el-input>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
        <div class="guide-table" style="margin-top:12px">
          <div class="guide-table__header">
            <span>抗压强度等级</span>
            <span>推荐 W/B</span>
          </div>
          <button
            v-for="row in guideRows"
            :key="row.grade"
            type="button"
            class="guide-table__row"
            :class="{ 'guide-table__row--active': store.strengthGrade === row.grade }"
            @click="handleGuideSelect(row.grade)"
          >
            <span>{{ row.label }}</span>
            <span>{{ row.wb }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 水胶比与外加剂 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><Drizzling /></el-icon>
        水胶比与外加剂
      </div>
      <div class="cs-section-body">
        <el-form label-position="top">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="水胶比 (W/B)">
                <el-input-number
                  :model-value="store.waterBinderRatio ?? undefined"
                  @update:model-value="value => store.waterBinderRatio = value ?? null"
                  :min="0.1" :max="0.5" :step="0.01" :precision="3"
                  :placeholder="waterBinderPlaceholder"
                  style="width:100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="外加剂掺量 α">
                <el-input-number
                  :model-value="store.admixtureRatio ?? undefined"
                  @update:model-value="value => store.admixtureRatio = value ?? null"
                  :min="0" :max="10" :step="0.1" :precision="2"
                  :placeholder="UHPC_INPUT_PLACEHOLDERS.admixtureRatio"
                  style="width:100%"
                >
                  <template #suffix><span class="unit-suffix">%</span></template>
                </el-input-number>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
        <div class="note-grid">
          <el-alert type="info" :closable="false">
            <template #title>W/B 取偏小值</template>
            <template #default>
              <div>1. 水泥 28d 抗压强度 &lt; 56 MPa</div>
              <div>2. 硅灰活性 &lt; 110%</div>
              <div>3. 砂压碎值 &gt; 10%</div>
            </template>
          </el-alert>
          <el-alert type="success" :closable="false">
            <template #title>W/B 取偏大值</template>
            <template #default>
              <div>1. 水泥 28d 抗压强度 &gt; 60 MPa</div>
              <div>2. 硅灰活性 &gt; 115%</div>
              <div>3. 砂压碎值 &lt; 7%</div>
            </template>
          </el-alert>
        </div>
        <div class="footer-actions">
          <el-button
            type="primary"
            :disabled="store.strengthGrade === null || store.waterBinderRatio === null || store.admixtureRatio === null"
            @click="emit('next-step')"
          >
            下一步
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.note-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 14px;
}
</style>
'''

# --- UhpcTabSandBinder ---
sb_tpl = '''<template>
  <div>
    <!-- S/B 参考范围 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><Grid /></el-icon>
        S/B 参考范围
      </div>
      <div class="cs-section-body">
        <div class="guide-table">
          <div class="guide-table__header">
            <span>抗压强度等级</span>
            <span>S/B</span>
          </div>
          <button
            v-for="row in guideRows"
            :key="row.grade"
            type="button"
            class="guide-table__row"
            :class="{ 'guide-table__row--active': store.strengthGrade === row.grade }"
            @click="handleGuideSelect(row.grade)"
          >
            <span>{{ row.label }}</span>
            <span>{{ row.range }}</span>
          </button>
        </div>
        <el-alert type="info" :closable="false" style="margin-top:12px">
          <template #default>
            当 UHPC 的抗拉强度有应变硬化需求，或砂的压碎值大于 10% 时，砂胶比宜取偏小值；反之可取偏大值。
          </template>
        </el-alert>
      </div>
    </div>

    <!-- 砂胶比 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><EditPen /></el-icon>
        砂胶比输入
      </div>
      <div class="cs-section-body">
        <el-form label-position="top">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="砂胶比 (S/B)">
                <el-input-number
                  :model-value="store.sandBinderRatio ?? undefined"
                  @update:model-value="value => store.sandBinderRatio = value ?? null"
                  :min="0.5" :max="2" :step="0.05" :precision="2"
                  :placeholder="UHPC_INPUT_PLACEHOLDERS.sandBinderRatio"
                  style="width:100%"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
        <div class="footer-actions">
          <el-button type="primary" :disabled="store.sandBinderRatio === null" @click="emit('next-step')">
            下一步
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* No local styles needed */
</style>
'''

# --- UhpcTabSteelFiber ---
sf_tpl = '''<template>
  <div>
    <!-- 钢纤维参考 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><Histogram /></el-icon>
        钢纤维参考
      </div>
      <div class="cs-section-body">
        <div class="guide-table">
          <div class="guide-table__header">
            <span>钢纤维等级</span>
            <span>体积掺量参考</span>
          </div>
          <button
            v-for="row in guideRows"
            :key="row.grade"
            type="button"
            class="guide-table__row"
            :class="{ 'guide-table__row--active': store.fiberStrengthGrade === row.grade }"
            @click="handleGuideSelect(row.grade)"
          >
            <span>{{ row.label }}</span>
            <span>{{ row.range }}</span>
          </button>
        </div>
        <el-alert type="info" :closable="false" style="margin-top:12px">
          <template #default>
            当 UHPC 的抗拉强度有应变硬化需求时，钢纤维体积掺量可取偏大值；当抗拉强度未达到设计要求时，应适当增加钢纤维用量。
          </template>
        </el-alert>
      </div>
    </div>

    <!-- 钢纤维用量 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><EditPen /></el-icon>
        钢纤维用量
      </div>
      <div class="cs-section-body">
        <el-form label-position="top">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item>
                <template #label>钢纤维体积掺量 V<sub>f</sub></template>
                <el-input-number
                  :model-value="store.steelFiberVolumeRatio ?? undefined"
                  @update:model-value="value => store.steelFiberVolumeRatio = value ?? null"
                  :min="0" :max="5" :step="0.1" :precision="2"
                  :placeholder="UHPC_INPUT_PLACEHOLDERS.steelFiberVolumeRatio"
                  style="width:100%"
                >
                  <template #suffix><span class="unit-suffix">%</span></template>
                </el-input-number>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item>
                <template #label>折算钢纤维质量 m<sub>f</sub></template>
                <el-input :model-value="steelFiberMassPreview !== null ? steelFiberMassPreview.toFixed(2) : ''" readonly class="computed-input">
                  <template #suffix><span class="unit-suffix">kg/m³</span></template>
                </el-input>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
        <div class="footer-actions">
          <el-button type="primary" :disabled="store.steelFiberVolumeRatio === null" @click="emit('next-step')">
            下一步
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* No local styles needed */
</style>
'''

def add_import_and_replace_template(filepath, new_tpl):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add CSS import if not present
    if "calc-tabs.css" not in content:
        # Find last import line in script section
        lines = content.split('\n')
        last_import_idx = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') and '</script>' not in line:
                last_import_idx = i
        if last_import_idx >= 0:
            lines.insert(last_import_idx + 1, "import '../../style/calc-tabs.css'")
            content = '\n'.join(lines)
    
    # Replace template+style
    tpl_idx = content.index('<template>')
    script_part = content[:tpl_idx]
    result = script_part + new_tpl
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(result)
    print(f'Updated {os.path.basename(filepath)}: {result.count(chr(10))} lines')

add_import_and_replace_template(os.path.join(BASE, 'UhpcTabWaterBinder.vue'), wb_tpl)
add_import_and_replace_template(os.path.join(BASE, 'UhpcTabSandBinder.vue'), sb_tpl)
add_import_and_replace_template(os.path.join(BASE, 'UhpcTabSteelFiber.vue'), sf_tpl)
print('Done UHPC tabs 1-3')
