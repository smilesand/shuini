<script setup lang="ts">
import { computed } from "vue";
import type { ChartData, StrengthRegression } from "../../composables/useHpcTrial";
import { formatNullableNumber } from "../../utils/format";

interface StrengthRelationRow {
  label: string;
  tagType: "primary" | "success" | "danger";
  wb: string;
  cw: string;
  strength: string;
}

const props = defineProps<{
  strengthRelationRows: StrengthRelationRow[];
  strengthRegression: StrengthRegression | null;
  chartData: ChartData | null;
  deltaWb: number;
  deltaBs: number;
  sTargetStrength: number | null;
  baseWb: number | null | undefined;
}>();

const fmt = formatNullableNumber;

const recommendStrengthText = computed(() => {
  if (props.sTargetStrength === null) {
    return null;
  }

  return (props.sTargetStrength + 0.1).toFixed(1);
});
</script>

<template>
  <el-divider content-position="left">
    <span style="font-size: 13px; color: #666">胶水比 - 抗压强度关系</span>
  </el-divider>

  <div class="materials-table-wrap">
    <el-table
      :data="props.strengthRelationRows"
      border
      size="small"
      table-layout="fixed"
      class="materials-table materials-table--relation"
    >
      <el-table-column label="组别" min-width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.tagType" size="small">
            {{ row.label }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column
        prop="wb"
        label="水胶比 W/B"
        min-width="110"
        align="center"
      />
      <el-table-column
        prop="cw"
        label="胶水比 C/W"
        min-width="110"
        align="center"
      />
      <el-table-column label="28d 强度 (MPa)" min-width="120" align="center">
        <template #default="{ row }">
          <span class="relation-strength">{{ row.strength }}</span>
        </template>
      </el-table-column>
    </el-table>
  </div>

  <template v-if="props.strengthRegression">
    <el-divider content-position="left">
      <span style="font-size: 13px; color: #666">回归分析与推荐</span>
    </el-divider>

    <div class="regression-grid">
      <div class="regression-card">
        <div class="regression-formula">
          f<sub>cu,0</sub> = {{ props.strengthRegression.a.toFixed(4) }} × (C/W)
          {{ props.strengthRegression.b >= 0 ? "+" : "" }}{{
            props.strengthRegression.b.toFixed(2)
          }}
        </div>
        <div style="font-size: 11px; color: #909399; margin-top: 4px">
          R² = {{ (props.strengthRegression.r2 * 100).toFixed(2) }}%
        </div>
      </div>

      <div
        v-if="props.strengthRegression.recommendWb !== null"
        class="regression-card recommend"
      >
        <span class="recommend-label">推荐水胶比</span>
        <span class="recommend-val">{{ props.strengthRegression.recommendWb.toFixed(2) }}</span>
        <span style="font-size: 11px; color: #909399">
          <template v-if="recommendStrengthText !== null">
            按 {{ recommendStrengthText }} MPa 取值（目标 {{ fmt(props.sTargetStrength, 1) }} MPa）
          </template>
          <template v-else>
            目标 {{ fmt(props.sTargetStrength, 1) }} MPa
          </template>
        </span>
      </div>

      <div
        v-if="props.strengthRegression.predictStrength !== null"
        class="regression-card predict"
      >
        <span class="recommend-label">推荐 W/B 强度预测</span>
        <span class="recommend-val"
          >{{ props.strengthRegression.predictStrength.toFixed(1) }} MPa</span
        >
        <span style="font-size: 11px; color: #909399">W/B = {{ fmt(props.strengthRegression.recommendWb, 4) }}</span>
      </div>
    </div>

    <div v-if="props.chartData" class="mini-chart-wrap">
      <svg viewBox="0 0 300 160" class="mini-chart">
        <line x1="50" y1="10" x2="50" y2="140" stroke="#dcdfe6" stroke-width="1" />
        <line x1="50" y1="140" x2="280" y2="140" stroke="#dcdfe6" stroke-width="1" />
        <line
          :x1="50 + ((props.chartData.bwRatios[2] - props.chartData.minBW) / props.chartData.rangeBW) * 230"
          :y1="140 - ((props.strengthRegression.a * props.chartData.bwRatios[2] + props.strengthRegression.b - props.chartData.minStrength) / props.chartData.rangeStrength) * 130"
          :x2="50 + ((props.chartData.bwRatios[1] - props.chartData.minBW) / props.chartData.rangeBW) * 230"
          :y2="140 - ((props.strengthRegression.a * props.chartData.bwRatios[1] + props.strengthRegression.b - props.chartData.minStrength) / props.chartData.rangeStrength) * 130"
          stroke="#2a5298"
          stroke-width="2"
          stroke-dasharray="6,3"
        />
        <circle
          v-for="(ratio, index) in props.chartData.bwRatios"
          :key="ratio + '-' + index"
          :cx="50 + ((ratio - props.chartData.minBW) / props.chartData.rangeBW) * 230"
          :cy="140 - ((props.chartData.strengths[index] - props.chartData.minStrength) / props.chartData.rangeStrength) * 130"
          r="5"
          fill="#2a5298"
          stroke="#fff"
          stroke-width="2"
        />
        <text x="160" y="155" text-anchor="middle" font-size="10" fill="#909399">
          胶水比 C/W
        </text>
        <text
          x="12"
          y="80"
          text-anchor="middle"
          font-size="10"
          fill="#909399"
          transform="rotate(-90, 12, 80)"
        >
          强度 MPa
        </text>
      </svg>
    </div>
  </template>

  <el-alert type="info" :closable="false" style="margin-top: 12px">
    <template #title>强度实验说明</template>
    <template #default>
      <p style="margin: 0; line-height: 1.8; font-size: 12px">
        以基准配合比为中心，按水胶比步长 {{ props.deltaWb }} 和砂率步长
        {{ props.deltaBs }}% 形成三组实验点。 水胶比调整时固定用水量，通过增减胶材总量并按原胶材比例分配到各胶凝材料来满足目标
        W/B；砂率调整时保持粗骨料与细骨料总量不变，一增一降完成调整。 根据三组
        (C/W, f<sub>cu</sub>) 数据进行线性回归，得到推荐水胶比，为后续“配合比校正与确认”提供依据。
      </p>
    </template>
  </el-alert>
</template>