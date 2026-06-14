binder_new = '''<template>
  <div>
    <!-- 依据参数 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><InfoFilled /></el-icon>
        依据参数
      </div>
      <div class="cs-section-body">
        <el-descriptions :column="3" size="small" border class="inherited-desc">
          <el-descriptions-item label="水胶比 (W/B)">
            <span class="inherited-val">{{ store.wb ? store.wb.toFixed(4) : '—' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="粗骨料用量 mg">
            <span class="inherited-val">{{ store.mg ? store.mg.toFixed(2) + ' kg' : '—' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="细骨料用量 ms">
            <span class="inherited-val">{{ store.ms ? store.ms.toFixed(2) + ' kg' : '—' }}</span>
          </el-descriptions-item>
        </el-descriptions>
        <el-alert
          v-if="!store.wb || !store.mg"
          title="请先完成水胶比和骨料计算"
          type="warning" show-icon :closable="false"
          style="margin-top:10px"
        />
      </div>
    </div>

    <!-- 胶凝材料组成 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><SetUp /></el-icon>
        胶凝材料组成
      </div>
      <div class="cs-section-body">
        <el-form label-position="top">
          <p style="font-size:12px;color:#909399;margin-bottom:12px">胶凝材料（质量分数 β，密度 ρ）</p>
          <el-row :gutter="20">
            <el-col :span="6">
              <el-form-item label="水泥掺量 β₁">
                <el-input-number :model-value="store.b1p ?? undefined" @update:model-value="v => store.b1p = v ?? null" :min="0" :max="100" :step="1" :precision="1" style="width:100%">
                  <template #suffix><span class="unit-suffix">%</span></template>
                </el-input-number>
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="水泥密度 ρ₁">
                <el-input-number :model-value="store.rho1 ?? undefined" @update:model-value="v => store.rho1 = v ?? null" :step="50" :precision="0" placeholder="如 3100" style="width:100%">
                  <template #suffix><span class="unit-suffix">kg/m³</span></template>
                </el-input-number>
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="粉煤灰掺量 β₂">
                <el-input-number :model-value="store.b2p ?? undefined" @update:model-value="v => store.b2p = v ?? null" :min="0" :max="100" :step="1" :precision="1" style="width:100%">
                  <template #suffix><span class="unit-suffix">%</span></template>
                </el-input-number>
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="粉煤灰密度 ρ₂">
                <el-input-number :model-value="store.rho2 ?? undefined" @update:model-value="v => store.rho2 = v ?? null" :step="50" :precision="0" placeholder="如 2200" style="width:100%">
                  <template #suffix><span class="unit-suffix">kg/m³</span></template>
                </el-input-number>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="6">
              <el-form-item label="微珠掺量 β₃">
                <el-input-number :model-value="store.b3p ?? undefined" @update:model-value="v => store.b3p = v ?? null" :min="0" :max="100" :step="1" :precision="1" style="width:100%">
                  <template #suffix><span class="unit-suffix">%</span></template>
                </el-input-number>
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="微珠密度 ρ₃">
                <el-input-number :model-value="store.rho3 ?? undefined" @update:model-value="v => store.rho3 = v ?? null" :step="50" :precision="0" placeholder="如 2600" style="width:100%">
                  <template #suffix><span class="unit-suffix">kg/m³</span></template>
                </el-input-number>
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="硅灰掺量 β₄">
                <el-input-number :model-value="store.b4p ?? undefined" @update:model-value="v => store.b4p = v ?? null" :min="0" :max="100" :step="1" :precision="1" style="width:100%">
                  <template #suffix><span class="unit-suffix">%</span></template>
                </el-input-number>
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="硅灰密度 ρ₄">
                <el-input-number :model-value="store.rho4 ?? undefined" @update:model-value="v => store.rho4 = v ?? null" :step="50" :precision="0" placeholder="如 2200" style="width:100%">
                  <template #suffix><span class="unit-suffix">kg/m³</span></template>
                </el-input-number>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="水泥密度 ρc">
                <el-input-number :model-value="store.rhoc ?? undefined" @update:model-value="v => store.rhoc = v ?? null" :step="50" :precision="0" placeholder="如 3100" style="width:100%">
                  <template #suffix><span class="unit-suffix">kg/m³</span></template>
                </el-input-number>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="含气量 Va">
                <el-input-number :model-value="store.va ?? undefined" @update:model-value="v => store.va = v ?? null" :min="0" :step="0.001" :precision="3" placeholder="如 0.010" style="width:100%">
                  <template #suffix><span class="unit-suffix">m³</span></template>
                </el-input-number>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </div>
    </div>

    <!-- 计算结果 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><Histogram /></el-icon>
        计算结果
      </div>
      <div class="cs-section-body">
        <el-form label-position="top">
          <p style="font-size:12px;color:#909399;margin-bottom:8px">中间量</p>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="水泥质量分数 βc">
                <el-input :value="store.bc ? (store.bc * 100).toFixed(1) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">%</span></template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="胶凝材料密度 ρb">
                <el-input :value="store.rhob ? store.rhob.toFixed(1) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">kg/m³</span></template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="浆体体积 Vp">
                <el-input :value="store.vp ? store.vp.toFixed(4) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">m³</span></template>
                </el-input>
              </el-form-item>
            </el-col>
          </el-row>
          <p style="font-size:12px;color:#909399;margin:12px 0 8px">各组分用量</p>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="胶凝材料用量 mb">
                <el-input :value="store.mb ? store.mb.toFixed(2) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">kg</span></template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="水泥用量 mc">
                <el-input :value="store.mc ? store.mc.toFixed(2) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">kg</span></template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="8" v-if="store.b1p > 0">
              <el-form-item label="矿物掺和料 m₁">
                <el-input :value="store.m1 ? store.m1.toFixed(2) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">kg</span></template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="8" v-if="store.b2p > 0">
              <el-form-item label="粉煤灰用量 m₂">
                <el-input :value="store.m2 ? store.m2.toFixed(2) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">kg</span></template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="8" v-if="store.b3p > 0">
              <el-form-item label="微珠用量 m₃">
                <el-input :value="store.m3 ? store.m3.toFixed(2) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">kg</span></template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="8" v-if="store.b4p > 0">
              <el-form-item label="硅灰用量 m₄">
                <el-input :value="store.m4 ? store.m4.toFixed(2) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">kg</span></template>
                </el-input>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>

        <el-alert type="info" :closable="false" style="margin-top:8px">
          <template #title>计算公式说明</template>
          <template #default>
            <Formula latex="\\beta_c = 1 - \\beta_1 - \\beta_2 - \\beta_3 - \\beta_4" style="margin-bottom:8px" />
            <Formula latex="\\rho_b = \\frac{1}{\\frac{\\beta_1}{\\rho_1} + \\frac{\\beta_2}{\\rho_2} + \\frac{\\beta_3}{\\rho_3} + \\frac{\\beta_4}{\\rho_4} + \\frac{\\beta_c}{\\rho_c}}" style="margin-bottom:8px" />
            <Formula latex="V_p = 1 - \\frac{m_g}{\\rho_g} - \\frac{m_s}{\\rho_s}" style="margin-bottom:8px" />
            <Formula latex="m_b = \\frac{V_p - V_a}{\\frac{1}{\\rho_b} + \\frac{W/B}{\\rho_w}}" style="margin-bottom:8px" />
            <Formula latex="m_i = m_b \\times \\beta_i \\quad (i = 1,2,3,4,c)" />
          </template>
        </el-alert>

        <div class="footer-actions">
          <el-button
            type="primary"
            :loading="store.loading"
            :disabled="!store.wb || !store.mg || !store.ms || !store.rhoc"
            @click="handleNext"
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
/* No local styles needed — all shared via calc-tabs.css */
</style>
'''

f = open(r'd:\Code\shuini_calculator\frontend\src\components\tabs\TabBinder.vue', 'r', encoding='utf-8')
content = f.read()
f.close()
tpl_idx = content.index('<template>')
script_part = content[:tpl_idx]
new_content = script_part + binder_new
open(r'd:\Code\shuini_calculator\frontend\src\components\tabs\TabBinder.vue', 'w', encoding='utf-8').write(new_content)
print('TabBinder done. Lines:', new_content.count('\n'))
