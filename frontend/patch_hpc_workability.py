import sys
from pathlib import Path

path = 'd:/Code/shuini_calculator/frontend/src/components/hpc-trial/HpcTrialWorkabilityTab.vue'
text = Path(path).read_text(encoding='utf-8')

marker = """      <!-- 工作性评价 -->
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
      </div>"""

insert = """      <!-- 合计说明 -->
      <div class="cs-section">
        <div class="cs-section-body" style="padding-top: 0;">
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
      </div>"""

text = text.replace(marker, insert)
Path(path).write_text(text, encoding='utf-8')
print("HpcTrialWorkabilityTab.vue patched")