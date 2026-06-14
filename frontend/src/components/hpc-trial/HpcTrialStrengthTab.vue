<script setup lang="ts">
import { computed } from "vue";
import HpcTrialStrengthAnalysisSection from "./HpcTrialStrengthAnalysisSection.vue";
import HpcTrialStrengthControlSection from "./HpcTrialStrengthControlSection.vue";
import HpcTrialStrengthMixSection from "./HpcTrialStrengthMixSection.vue";
import { useHpcTrialContext } from "../../composables/context";
import { formatNullableNumber } from "../../utils/format";
import '../../style/calc-tabs.css'

const {
  hasData,
  baseWb,
  baseBs,
  deltaWb,
  deltaBs,
  strength0,
  strengthP,
  strengthN,
  sTargetStrength,
  workabilityResult,
  strengthMixes,
  strengthRegression,
  chartData,
  resetStrength,
} = useHpcTrialContext();

const fmt = formatNullableNumber;

const strengthDisplayOrder = [1, 0, 2] as const;

const strengthGroupMeta = [
  { headerLabel: "基准", relationLabel: "基准", tagType: "primary" as const },
  { headerLabel: "+Δ 组", relationLabel: "+Δ", tagType: "success" as const },
  { headerLabel: "-Δ 组", relationLabel: "-Δ", tagType: "danger" as const },
];

const materialColumns = [
  { key: "mc", label: "水泥" },
  { key: "m1", label: "粉煤灰" },
  { key: "m2", label: "矿粉" },
  { key: "m3", label: "微珠" },
  { key: "m4", label: "硅灰" },
  { key: "mg", label: "粗骨料" },
  { key: "ms", label: "细骨料" },
  { key: "mw", label: "水" },
  { key: "ma", label: "外加剂" },
];

const mixColumns = [...materialColumns, { key: "total", label: "合计" }];

function createTableCell(
  value: number | null | undefined,
  digits = 2,
  options: {
    changed?: boolean;
    emphasized?: boolean;
  } = {},
) {
  return {
    text: fmt(value, digits),
    changed: options.changed,
    emphasized: options.emphasized,
  };
}

const baseMaterialRows = computed(() => [
  {
    mc: createTableCell(workabilityResult.value.mc),
    m1: createTableCell(workabilityResult.value.m1),
    m2: createTableCell(workabilityResult.value.m2),
    m3: createTableCell(workabilityResult.value.m3),
    m4: createTableCell(workabilityResult.value.m4),
    mg: createTableCell(workabilityResult.value.mg),
    ms: createTableCell(workabilityResult.value.ms),
    mw: createTableCell(workabilityResult.value.mw),
    ma: createTableCell(workabilityResult.value.ma),
  },
]);

const strengthDisplayRows = computed(() =>
  strengthDisplayOrder.flatMap((sourceIndex) => {
    const mix = strengthMixes.value[sourceIndex];

    if (!mix) {
      return [];
    }

    return [
      {
        sourceIndex,
        mix,
        meta: strengthGroupMeta[sourceIndex],
        strengthValue:
          sourceIndex === 0
            ? strength0.value
            : sourceIndex === 1
              ? strengthP.value
              : strengthN.value,
      },
    ];
  }),
);

const strengthMixTableRows = computed(() =>
  strengthDisplayRows.value.map(({ sourceIndex, mix, meta }) => ({
    headerLabel: meta.headerLabel,
    headerType: meta.tagType,
    summary: `W/B=${fmt(mix.wb, 4)}  βs=${fmt(mix.bs)}%`,
    rows: [
      {
        // 调整水胶比后，变化的是胶材总量及其分项分配；水量保持不变。
        mc: createTableCell(mix.mc, 2, { changed: sourceIndex !== 0 }),
        m1: createTableCell(mix.m1, 2, { changed: sourceIndex !== 0 }),
        m2: createTableCell(mix.m2, 2, { changed: sourceIndex !== 0 }),
        m3: createTableCell(mix.m3, 2, { changed: sourceIndex !== 0 }),
        m4: createTableCell(mix.m4, 2, { changed: sourceIndex !== 0 }),
        mg: createTableCell(mix.mg, 2, { changed: sourceIndex !== 0 }),
        ms: createTableCell(mix.ms, 2, { changed: sourceIndex !== 0 }),
        mw: createTableCell(mix.mw),
        ma: createTableCell(mix.ma, 2, { changed: sourceIndex !== 0 }),
        total: createTableCell(mix.total, 2, { emphasized: true }),
      },
    ],
  })),
);

const strengthRelationRows = computed(() =>
  strengthDisplayRows.value.map(({ mix, meta, strengthValue }) => ({
    label: meta.relationLabel,
    tagType: meta.tagType,
    wb: fmt(mix.wb, 4),
    cw: mix.wb ? fmt(1 / mix.wb, 4) : "—",
    strength: fmt(strengthValue, 1),
  })),
);
</script>

<template>
  <div>
    <el-alert
      v-if="!hasData"
      title="请先在配比计算 → 高性能混凝土中完成配合比计算。"
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
