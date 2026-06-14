import sys
from pathlib import Path

filepath = 'd:/Code/shuini_calculator/frontend/src/components/hpc-trial/HpcTrialCorrectionTab.vue'
text = Path(filepath).read_text(encoding='utf-8')

marker1 = """  labMix,
  resetCorrection,
} = useHpcTrialContext()"""

insert1 = """  labMix,
  resetCorrection,
  evalStrength28d,
  evalSlump,
  evalSpread,
  evalWorkabilityDesc,
} = useHpcTrialContext()"""

text = text.replace(marker1, insert1)

marker2 = """          <el-alert type="info" :closable="false" style="margin-top: 14px">
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
</template>"""

insert2 = """          <el-alert type="info" :closable="false" style="margin-top: 14px">
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

      <!-- 工作性与性能评价 (HPC) -->
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

text = text.replace(marker2, insert2)

Path(filepath).write_text(text, encoding='utf-8')
print("HPC patched")
