import sys
from pathlib import Path

path = 'd:/Code/shuini_calculator/frontend/src/components/hpc-trial/HpcTrialCorrectionTab.vue'
text = Path(path).read_text(encoding='utf-8')

marker_imports = """  labMix,
  resetCorrection,
  evalStrength28d,
  evalSlump,
  evalSpread,
  evalWorkabilityDesc,
} = useHpcTrialContext()"""

insert_imports = """  labMix,
  resetCorrection,
  evalStrength28d,
  slumpMeasured,
  spreadMeasured,
  workabilityNote,
  workabilityEvaluation,
  selectedWorkabilityReference,
} = useHpcTrialContext()"""

text = text.replace(marker_imports, insert_imports)

marker_ui = """      <!-- 工作性与性能评价 (HPC) -->
      <div class="cs-section">
        <div class="cs-section-head">
          <el-icon><DataAnalysis /></el-icon>
          工作性与性能评价（实验室配合比基准）
        </div>
        <div class="cs-section-body">
          <el-row :gutter="20" style="margin-bottom:12px">
            <el-col :span="8">
              <div class="density-field" style="display:flex;flex-direction:column;gap:6px;">
                <div class="density-field__label" style="font-size:13px;font-weight:600;color:#374151;">28d抗压强度</div>
                <el-input-number
                  v-model="evalStrength28d"
                  :min="0" :max="400" :step="1" :precision="1"
                  placeholder="例如: 65"
                  style="width: 100%"
                />
                <div class="density-field__unit" style="font-size:11px;color:#9ca3af;">MPa</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="density-field" style="display:flex;flex-direction:column;gap:6px;">
                <div class="density-field__label" style="font-size:13px;font-weight:600;color:#374151;">坍落度</div>
                <el-input-number
                  v-model="evalSlump"
                  :min="0" :max="300" :step="5" :precision="0"
                  placeholder="例如: 220"
                  style="width: 100%"
                 />
                <div class="density-field__unit" style="font-size:11px;color:#9ca3af;">mm</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="density-field" style="display:flex;flex-direction:column;gap:6px;">
                <div class="density-field__label" style="font-size:13px;font-weight:600;color:#374151;">扩展度</div>
                <el-input-number
                  v-model="evalSpread"
                  :min="0" :max="900" :step="10" :precision="0"
                  placeholder="例如: 550"
                  style="width: 100%"
                />
                <div class="density-field__unit" style="font-size:11px;color:#9ca3af;">mm</div>
              </div>
            </el-col>
          </el-row>

          <div class="density-field" style="display:flex;flex-direction:column;gap:6px;margin-top:16px;">
            <div class="density-field__label" style="font-size:13px;font-weight:600;color:#374151;">工作性综合描述</div>
            <el-input
              type="textarea"
              :rows="3"
              v-model="evalWorkabilityDesc"
              placeholder="例如：拌合物保水性良好，无泌水、无抓底现象，流动性完全满足施工要求..."
            />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>"""

insert_ui = """      <!-- 工作性与性能评价 (HPC) -->
      <div class="cs-section">
        <div class="cs-section-head">
          <el-icon><DataAnalysis /></el-icon>
          工作性与性能评价（实验室配合比基准）
        </div>
        <div class="cs-section-body">
          <el-form label-position="top" size="default">
            <el-row :gutter="20">
              <el-col :span="8">
                <el-form-item>
                  <template #label>28d抗压强度</template>
                  <el-input-number
                    v-model="evalStrength28d"
                    :min="0" :max="400" :step="1" :precision="1"
                    placeholder="如 65"
                    style="width: 100%"
                  >
                    <template #suffix><span class="unit-suffix">MPa</span></template>
                  </el-input-number>
                </el-form-item>
              </el-col>
              <el-col :span="8">
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
              <el-col :span="8">
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
                <div class="trial-workability-evaluation" style="display:flex;align-items:center;gap:12px;">
                  <span class="trial-workability-evaluation__label" style="font-weight:bold;color:#374151;">工作性评价状态：</span>
                  <el-tag :type="workabilityEvaluation.tagType" size="small">{{ workabilityEvaluation.label }}</el-tag>
                  <span class="trial-workability-evaluation__detail" style="font-size:12px;color:#6b7280;">
                    {{ selectedWorkabilityReference ? workabilityEvaluation.detail : '请先在"骨料用量"中选择 Vg 参考范围。' }}
                  </span>
                </div>
              </el-col>
            </el-row>
          </el-form>
        </div>
      </div>
    </template>
  </div>
</template>"""

text = text.replace(marker_ui, insert_ui)
Path(path).write_text(text, encoding='utf-8')
print("HpcTrialCorrectionTab.vue updated")