admix_new = '''<template>
  <div>
    <!-- 依据参数 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><Drizzling /></el-icon>
        依据参数
      </div>
      <div class="cs-section-body">
        <el-descriptions :column="2" size="small" border class="inherited-desc">
          <el-descriptions-item label="胶凝材料用量 mb">
            <span class="inherited-val">{{ store.mb ? store.mb.toFixed(2) + ' kg' : '—' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="水胶比 (W/B)">
            <span class="inherited-val">{{ store.wb ? store.wb.toFixed(4) : '—' }}</span>
          </el-descriptions-item>
        </el-descriptions>
        <el-alert
          v-if="!store.mb || !store.wb"
          title="请先完成胶凝材料计算"
          type="warning" show-icon :closable="false"
          style="margin-top:10px"
        />
      </div>
    </div>

    <!-- 外加剂参数 -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><EditPen /></el-icon>
        外加剂参数
      </div>
      <div class="cs-section-body">
        <el-form label-position="top">
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="外加剂掺量 α">
                <el-input-number
                  :model-value="store.alpha ?? undefined"
                  @update:model-value="v => store.alpha = v ?? null"
                  :min="0" :step="0.1" :precision="2"
                  placeholder="如 1.5"
                  style="width:100%"
                >
                  <template #suffix><span class="unit-suffix">%</span></template>
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
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item>
                <template #label>用水量 m<sub>w</sub></template>
                <el-input :value="store.mw ? store.mw.toFixed(2) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">kg</span></template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item>
                <template #label>外加剂用量 m<sub>a</sub></template>
                <el-input :value="store.ma ? store.ma.toFixed(2) : ''" readonly placeholder="—" class="computed-input">
                  <template #suffix><span class="unit-suffix">kg</span></template>
                </el-input>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>

        <!-- 总合计 -->
        <div class="total-card">
          <span class="total-label">每立方混凝土材料合计</span>
          <span class="total-val">{{ store.totalMass ? store.totalMass.toFixed(2) + ' kg/m³' : '—' }}</span>
        </div>

        <el-alert type="info" :closable="false" style="margin-top:12px">
          <template #title>计算公式说明</template>
          <template #default>
            <Formula latex="m_w = m_b \\times W\\!/\\!B" style="margin-bottom:8px" />
            <Formula latex="m_a = m_b \\times \\alpha" />
          </template>
        </el-alert>

        <el-alert
          v-if="store.mw !== null"
          title="全部计算已完成！可在右侧汇总栏查看完整配比结果。"
          type="success"
          :closable="false"
          show-icon
          style="margin-top:12px"
        />

        <div class="footer-actions">
          <el-button
            type="primary"
            :loading="store.loading"
            :disabled="!store.mb || !store.wb || !store.alpha"
            @click="handleFinish"
          >
            {{ saveButtonText }}
            <el-icon><FolderAdd /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <el-dialog v-model="saveVisible" title="保存配比记录" width="400px">
      <el-form @submit.prevent="persistRecord(saveName)">
        <el-form-item label="配比名称">
          <el-input v-model="saveName" placeholder="例如：C80 高性能混凝土方案" maxlength="50" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="saveVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" :disabled="!saveName.trim()" @click="persistRecord(saveName)">
          确认保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.total-card {
  margin-top: 16px;
  padding: 16px 20px;
  background: linear-gradient(135deg, #1e3c72, #2a5298);
  border-radius: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.total-label {
  font-size: 14px;
  color: rgba(255,255,255,0.85);
  font-weight: 500;
}
.total-val {
  font-size: 22px;
  font-weight: 800;
  color: #fff;
}
</style>
'''

f = open(r'd:\Code\shuini_calculator\frontend\src\components\tabs\TabWaterAdmix.vue', 'r', encoding='utf-8')
content = f.read()
f.close()
tpl_idx = content.index('<template>')
script_part = content[:tpl_idx]
new_content = script_part + admix_new
open(r'd:\Code\shuini_calculator\frontend\src\components\tabs\TabWaterAdmix.vue', 'w', encoding='utf-8').write(new_content)
print('TabWaterAdmix done. Lines:', new_content.count('\n'))
