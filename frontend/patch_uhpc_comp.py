import sys
from pathlib import Path

filepath = 'd:/Code/shuini_calculator/frontend/src/components/uhpc-trial/UhpcTrialCorrectionTab.vue'
text = Path(filepath).read_text(encoding='utf-8')

marker1 = """  labMix: UhpcTrialMixRowRes | null
  designStr: number
}>()

const emit = defineEmits<{
  (e: 'update:corrBase', v: 'trial' | 'wbRec' | 'sfRec'): void
  (e: 'update:measuredDensity', v: number | null): void
}>()"""

insert1 = """  labMix: UhpcTrialMixRowRes | null
  designStr: number
  evalStrength28d: number | null
  evalSlump: number | null
  evalSpread: number | null
  evalWorkabilityDesc: string
}>()

const emit = defineEmits<{
  (e: 'update:corrBase', v: 'trial' | 'wbRec' | 'sfRec'): void
  (e: 'update:measuredDensity', v: number | null): void
  (e: 'update:evalStrength28d', v: number | null): void
  (e: 'update:evalSlump', v: number | null): void
  (e: 'update:evalSpread', v: number | null): void
  (e: 'update:evalWorkabilityDesc', v: string): void
}>()"""

text = text.replace(marker1, insert1)

marker2 = """        <el-alert type="info" :closable="false" style="margin-top: 14px">
          <b>注：</b>
          实测值与计算值之差的绝对值不超过计算值的 2%，则维持调整配合比，即为实验室配合比；
          超过 2%，各材料用量均需乘以校正系数（k = 实测值 / 计算值）。
        </el-alert>
      </div>
    </div>
  </div>
</template>"""

insert2 = """        <el-alert type="info" :closable="false" style="margin-top: 14px">
          <b>注：</b>
          实测值与计算值之差的绝对值不超过计算值的 2%，则维持调整配合比，即为实验室配合比；
          超过 2%，各材料用量均需乘以校正系数（k = 实测值 / 计算值）。
        </el-alert>
      </div>
    </div>

    <!-- 工作性与性能评价 (UHPC) -->
    <div class="cs-section">
      <div class="cs-section-head">
        <el-icon><DataAnalysis /></el-icon>
        工作性与性能评价（实验室配合比基准）
      </div>
      <div class="cs-section-body">
        <el-row :gutter="20" style="margin-bottom:12px">
          <el-col :span="8">
            <div class="density-field">
              <div class="density-field__label">28d抗压强度</div>
              <el-input-number
                :model-value="evalStrength28d ?? undefined"
                @update:model-value="v => emit('update:evalStrength28d', v ?? null)"
                :min="0" :max="400" :step="1" :precision="1"
                placeholder="例如: 135"
                style="width: 100%"
              />
              <div class="density-field__unit">MPa</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="density-field">
              <div class="density-field__label">坍落度</div>
              <el-input-number
                :model-value="evalSlump ?? undefined"
                @update:model-value="v => emit('update:evalSlump', v ?? null)"
                :min="0" :max="300" :step="5" :precision="0"
                placeholder="例如: 260"
                style="width: 100%"
              />
              <div class="density-field__unit">mm</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="density-field">
              <div class="density-field__label">扩展度</div>
              <el-input-number
                :model-value="evalSpread ?? undefined"
                @update:model-value="v => emit('update:evalSpread', v ?? null)"
                :min="0" :max="900" :step="10" :precision="0"
                placeholder="例如: 650"
                style="width: 100%"
              />
              <div class="density-field__unit">mm</div>
            </div>
          </el-col>
        </el-row>

        <div class="density-field" style="margin-top: 16px">
          <div class="density-field__label">工作性综合描述</div>
          <el-input
            type="textarea"
            :rows="3"
            :model-value="evalWorkabilityDesc"
            @update:model-value="v => emit('update:evalWorkabilityDesc', v)"
            placeholder="例如：拌合物粘聚性良好，流动性优异，无泌水、离析现象，钢纤维分散均匀..."
          />
        </div>
      </div>
    </div>
  </div>
</template>"""

text = text.replace(marker2, insert2)
Path(filepath).write_text(text, encoding='utf-8')
print("UHPC component patched")
