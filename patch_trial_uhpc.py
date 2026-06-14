f = open(r'd:\Code\shuini_calculator\frontend\src\views\TrialUhpcView.vue', 'r', encoding='utf-8')
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
        lines.insert(last_import_idx + 1, "import '../style/calc-tabs.css'")
        content = '\n'.join(lines)

tpl_idx = content.index('<template>')
script_part = content[:tpl_idx]

# Get style section
style_idx = content.rindex('<style scoped>')
style_part = content[style_idx:]

new_template = r'''<template>
  <div class="trial-view">
    <!-- ─── Main card ─── -->
    <div class="trial-main">
      <el-card :body-style="{ padding: 0 }" class="trial-card" shadow="never">
        <!-- Card header -->
        <template #header>
          <div class="card-header">
            <div class="header-left">
              <span class="header-badge">UHPC Trial</span>
              <div>
                <div class="header-title">超高性能混凝土试配</div>
                <div v-if="store.hasResults" class="header-meta">
                  <span>UC{{ store.strengthGrade }}</span>
                  <span class="dot">·</span>
                  <span>W/B = {{ wb.toFixed(3) }}</span>
                  <span class="dot">·</span>
                  <span>S/B = {{ sb.toFixed(2) }}</span>
                  <span class="dot">·</span>
                  <span>α = {{ alpha.toFixed(2) }}%</span>
                  <span class="dot">·</span>
                  <span>钢纤维 {{ store.steelFiberVolumeRatio?.toFixed(2) ?? '—' }}%</span>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- No data state -->
        <div v-if="!store.hasResults" class="no-data">
          <el-empty description="请先在超高性能混凝土配合比计算页完成参数计算">
            <el-button type="primary" @click="goToCalc">
              <el-icon><ArrowRight /></el-icon>
              前往配合比计算
            </el-button>
          </el-empty>
        </div>

        <template v-else>
          <el-tabs v-model="activeTab" type="card" class="trial-tabs">

            <!-- ══════════════ Tab 1: 工作性试验 ══════════════ -->
            <el-tab-pane label="工作性试验" name="workability">
              <div class="pane-wrap">
                <!-- 计算配合比 -->
                <div class="cs-section">
                  <div class="cs-section-head">
                    <el-icon><Grid /></el-icon>
                    计算配合比
                  </div>
                  <div class="cs-section-body">
                    <p class="pane-lead">以配合比计算结果为基准，按需调整砂胶比和外加剂掺量，生成试拌配合比。</p>
                    <div class="mix-label">每方用量 <span class="unit-tag">kg/m³</span></div>
                    <div class="mix-grid mix-grid--calc">
                      <div v-for="k in MAT_KEYS" :key="k" class="mix-cell">
                        <div class="mix-cell__head">{{ MAT_LABELS[k] }}</div>
                        <div class="mix-cell__val">{{ fmt(storeVal(k)) }}</div>
                      </div>
                      <div class="mix-cell mix-cell--total">
                        <div class="mix-cell__head">合计</div>
                        <div class="mix-cell__val">{{ fmt(store.materialMasses.total) }}</div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 试拌调整 -->
                <div class="cs-section">
                  <div class="cs-section-head">
                    <el-icon><Edit /></el-icon>
                    试拌调整
                  </div>
                  <div class="cs-section-body">
                    <el-row :gutter="32">
                      <el-col :span="12">
                        <el-form-item>
                          <template #label>
                            <span class="adj-label">砂胶比 (S/B)</span>
                            <span class="adj-orig">计算值：{{ sb.toFixed(2) }}</span>
                          </template>
                          <el-input-number
                            :model-value="adjustedSB ?? undefined"
                            @update:model-value="v => adjustedSB = v ?? null"
                            :min="0.5" :max="2" :step="0.05" :precision="2"
                            :placeholder="sb.toFixed(2)"
                            style="width: 100%"
                          />
                        </el-form-item>
                      </el-col>
                      <el-col :span="12">
                        <el-form-item>
                          <template #label>
                            <span class="adj-label">外加剂掺量 α (%)</span>
                            <span class="adj-orig">计算值：{{ alpha.toFixed(2) }}%</span>
                          </template>
                          <el-input-number
                            :model-value="adjustedAlpha ?? undefined"
                            @update:model-value="v => adjustedAlpha = v ?? null"
                            :min="0" :max="10" :step="0.1" :precision="2"
                            :placeholder="alpha.toFixed(2)"
                            style="width: 100%"
                          />
                        </el-form-item>
                      </el-col>
                    </el-row>
                  </div>
                </div>

                <!-- 试拌配合比 -->
                <div class="cs-section">
                  <div class="cs-section-head">
                    <el-icon><DataAnalysis /></el-icon>
                    试拌配合比
                  </div>
                  <div class="cs-section-body">
                    <div class="mix-label">根据调整后的砂胶比和外加剂掺量重新计算 <span class="unit-tag">kg/m³</span></div>
                    <div class="mix-grid mix-grid--trial">
                      <div v-for="k in MAT_KEYS" :key="k" class="mix-cell">
                        <div class="mix-cell__head">{{ MAT_LABELS[k] }}</div>
                        <div class="mix-cell__val">{{ fmt(mixVal(trialMix, k)) }}</div>
                      </div>
                      <div class="mix-cell mix-cell--total">
                        <div class="mix-cell__head">合计</div>
                        <div class="mix-cell__val">{{ fmt(trialMix?.total) }}</div>
                      </div>
                    </div>
                    <el-alert type="info" :closable="false" style="margin-top: 14px">
                      水泥、粉煤灰、微珠、硅灰、砂的用量根据调整后的砂胶比和各自质量分数计算；
                      外加剂用量根据调整后的胶材用量和外加剂掺量计算；钢纤维用量保持不变。
                    </el-alert>
                  </div>
                </div>
              </div>
            </el-tab-pane>

            <!-- ══════════════ Tab 2: 强度试验 ══════════════ -->
            <el-tab-pane label="强度试验" name="strength">
              <div class="pane-wrap">
                <!-- 强度试验配合比 -->
                <div class="cs-section">
                  <div class="cs-section-head">
                    <el-icon><List /></el-icon>
                    强度试验配合比
                  </div>
                  <div class="cs-section-body">
                    <p class="pane-lead">
                      在试拌配合比基础上分别调整水胶比（±0.01）和硅灰用量（±5%），
                      完成浇注和养护后测定各组抗压强度并填入表格，系统据此推荐最优参数。
                    </p>
                    <div class="variant-list">
                      <div v-for="(v, i) in variants" :key="i" class="variant-row">
                        <div class="vrow-tag" :class="v.tagCls">{{ v.label }}</div>
                        <div class="vrow-mix">
                          <div class="mix-grid mix-grid--variant">
                            <div v-for="k in MAT_KEYS" :key="k" class="mix-cell mix-cell--sm">
                              <div class="mix-cell__head">{{ MAT_LABELS[k] }}</div>
                              <div class="mix-cell__val">{{ fmt(mixVal(v.mix, k)) }}</div>
                            </div>
                          </div>
                        </div>
                        <div class="vrow-input">
                          <el-input-number
                            :model-value="v.sRef.value ?? undefined"
                            @update:model-value="val => v.sRef.value = val ?? null"
                            :min="0" :max="400" :step="1" :precision="1"
                            placeholder="实测强度"
                            style="width: 120px"
                          />
                          <span class="unit-s">MPa</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 强度分析与推荐 -->
                <div class="cs-section">
                  <div class="cs-section-head">
                    <el-icon><TrendCharts /></el-icon>
                    强度分析与推荐
                  </div>
                  <div class="cs-section-body">
                    <el-row :gutter="20" style="margin-bottom: 16px">
                      <el-col :span="12">
                        <table class="sum-tbl">
                          <thead><tr><th>水胶比</th><th>抗压强度（MPa）</th></tr></thead>
                          <tbody>
                            <tr>
                              <td>{{ (wb + 0.01).toFixed(3) }}</td>
                              <td>{{ sWbPlus !== null ? fmt(sWbPlus) : '—' }}</td>
                            </tr>
                            <tr>
                              <td>{{ (wb - 0.01).toFixed(3) }}</td>
                              <td>{{ sWbMinus !== null ? fmt(sWbMinus) : '—' }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </el-col>
                      <el-col :span="12">
                        <table class="sum-tbl">
                          <thead><tr><th>硅灰用量（kg）</th><th>抗压强度（MPa）</th></tr></thead>
                          <tbody>
                            <tr>
                              <td>{{ vSfPlus ? fmt(vSfPlus.silicaFume) : '—' }}</td>
                              <td>{{ sSfPlus !== null ? fmt(sSfPlus) : '—' }}</td>
                            </tr>
                            <tr>
                              <td>{{ vSfMinus ? fmt(vSfMinus.silicaFume) : '—' }}</td>
                              <td>{{ sSfMinus !== null ? fmt(sSfMinus) : '—' }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </el-col>
                    </el-row>
                    <div class="rec-row">
                      <div class="rec-card">
                        <div class="rec-card__label">推荐水胶比</div>
                        <div class="rec-card__val">{{ recWb !== null ? recWb.toFixed(3) : '—' }}</div>
                        <div class="rec-card__sub">线性插值</div>
                      </div>
                      <div class="rec-card">
                        <div class="rec-card__label">推荐硅灰用量</div>
                        <div class="rec-card__val">{{ recSf !== null ? recSf.toFixed(1) + ' kg' : '—' }}</div>
                        <div class="rec-card__sub">线性插值</div>
                      </div>
                      <div class="rec-card rec-card--target">
                        <div class="rec-card__label">配制强度目标</div>
                        <div class="rec-card__val">{{ designStr.toFixed(1) }} MPa</div>
                        <div class="rec-card__sub">UC{{ store.strengthGrade }} × 1.10</div>
                      </div>
                    </div>
                    <el-alert type="info" :closable="false" style="margin-top: 14px">
                      <b>说明：</b>选择比配制强度（{{ fmt(designStr) }} MPa）略高的水胶比或硅灰质量，
                      优先考虑水胶比调整。在表格中填入各配比强度，系统将自动推荐最优参数。
                    </el-alert>
                  </div>
                </div>
              </div>
            </el-tab-pane>

            <!-- ══════════════ Tab 3: 配合比校正与确定 ══════════════ -->
            <el-tab-pane label="配合比校正与确定" name="correction">
              <div class="pane-wrap">
                <!-- 调整配合比基准 -->
                <div class="cs-section">
                  <div class="cs-section-head">
                    <el-icon><SetUp /></el-icon>
                    选择调整配合比基准
                  </div>
                  <div class="cs-section-body">
                    <div class="base-select-panel">
                      <el-radio-group v-model="corrBase" class="base-radios">
                        <el-radio value="trial">试拌配合比</el-radio>
                        <el-radio value="wbRec" :disabled="recWb === null">
                          推荐水胶比配合比
                          <span v-if="recWb !== null" class="radio-hint">（W/B = {{ recWb.toFixed(3) }}）</span>
                        </el-radio>
                        <el-radio value="sfRec" :disabled="recSf === null">
                          推荐硅灰配合比
                          <span v-if="recSf !== null" class="radio-hint">（硅灰 {{ recSf.toFixed(1) }} kg）</span>
                        </el-radio>
                      </el-radio-group>
                    </div>
                    <div class="mix-label" style="margin-top:14px">调整配合比 <span class="unit-tag">kg/m³</span></div>
                    <div v-if="corrMix" class="mix-grid mix-grid--trial">
                      <div v-for="k in MAT_KEYS" :key="k" class="mix-cell">
                        <div class="mix-cell__head">{{ MAT_LABELS[k] }}</div>
                        <div class="mix-cell__val">{{ fmt(corrMix[k]) }}</div>
                      </div>
                      <div class="mix-cell mix-cell--total">
                        <div class="mix-cell__head">合计</div>
                        <div class="mix-cell__val">{{ fmt(corrMix.total) }}</div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 密度校正 -->
                <div class="cs-section">
                  <div class="cs-section-head">
                    <el-icon><Odometer /></el-icon>
                    表观密度校正
                  </div>
                  <div class="cs-section-body">
                    <el-row :gutter="20" style="margin-bottom: 12px">
                      <el-col :span="8">
                        <div class="density-field">
                          <div class="density-field__label">拌合物表观密度实测值</div>
                          <el-input-number
                            :model-value="measuredDensity ?? undefined"
                            @update:model-value="v => measuredDensity = v ?? null"
                            :min="1500" :max="3500" :step="10" :precision="0"
                            placeholder="如 2510"
                            style="width: 100%"
                          />
                          <div class="density-field__unit">kg/m³</div>
                        </div>
                      </el-col>
                      <el-col :span="8">
                        <div class="density-field">
                          <div class="density-field__label">拌合物表观密度计算值</div>
                          <el-input :value="fmt(calcDensity)" readonly class="calc-inp" />
                          <div class="density-field__unit">kg/m³</div>
                        </div>
                      </el-col>
                      <el-col :span="8">
                        <div class="density-field">
                          <div class="density-field__label">校正系数 k</div>
                          <el-input
                            :value="corrFactor !== null ? corrFactor.toFixed(4) : '—'"
                            readonly class="calc-inp"
                          />
                          <div class="density-field__unit">实测 / 计算</div>
                        </div>
                      </el-col>
                    </el-row>
                    <div
                      v-if="corrFactor !== null"
                      class="corr-status"
                      :class="needsCorr ? 'corr-status--warn' : 'corr-status--ok'"
                    >
                      <el-icon :size="16">
                        <component :is="needsCorr ? 'Warning' : 'CircleCheck'" />
                      </el-icon>
                      <span v-if="needsCorr">
                        偏差
                        {{ (Math.abs(measuredDensity! - calcDensity!) / calcDensity! * 100).toFixed(2) }}%
                        已超过 2%，实验室配合比已乘以校正系数 <b>{{ corrFactor.toFixed(4) }}</b>。
                      </span>
                      <span v-else>偏差未超过 2%，实验室配合比维持调整配合比不变。</span>
                    </div>
                  </div>
                </div>

                <!-- 实验室配合比 -->
                <div class="cs-section">
                  <div class="cs-section-head">
                    <el-icon><DocumentChecked /></el-icon>
                    实验室配合比
                  </div>
                  <div class="cs-section-body">
                    <template v-if="labMix">
                      <div class="mix-label" :class="needsCorr ? 'mix-grid--corrected' : 'mix-grid--trial'" style="margin-bottom:8px">
                        <span class="unit-tag">kg/m³{{ needsCorr ? '（已按校正系数调整）' : '' }}</span>
                      </div>
                      <div class="mix-grid" :class="needsCorr ? 'mix-grid--corrected' : 'mix-grid--trial'">
                        <div v-for="k in MAT_KEYS" :key="k" class="mix-cell">
                          <div class="mix-cell__head">{{ MAT_LABELS[k] }}</div>
                          <div class="mix-cell__val">{{ fmt(labMix[k]) }}</div>
                        </div>
                        <div class="mix-cell mix-cell--total">
                          <div class="mix-cell__head">合计</div>
                          <div class="mix-cell__val">{{ fmt(labMix.total) }}</div>
                        </div>
                      </div>
                    </template>
                    <el-alert
                      v-else
                      type="warning"
                      :closable="false"
                      title="请录入实测表观密度以生成实验室配合比。"
                      style="margin-bottom: 12px"
                    />
                    <el-alert type="info" :closable="false" style="margin-top: 14px">
                      <b>注：</b>
                      实测值与计算值之差的绝对值不超过计算值的 2%，则维持调整配合比，即为实验室配合比；
                      超过 2%，各材料用量均需乘以校正系数（k = 实测值 / 计算值）。
                    </el-alert>
                  </div>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>

          <!-- Footer navigation -->
          <div class="trial-footer">
            <el-button v-if="!isFinalTab" type="primary" @click="handleNext">
              下一步
              <el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>
        </template>
      </el-card>
    </div>

    <!-- ─── Sidebar ─── -->
    <div class="trial-sidebar">
      <UhpcSidebarSummary />
    </div>
  </div>
</template>

'''

result = script_part + new_template + style_part
open(r'd:\Code\shuini_calculator\frontend\src\views\TrialUhpcView.vue', 'w', encoding='utf-8').write(result)
print('Done TrialUhpcView:', result.count('\n'), 'lines')
