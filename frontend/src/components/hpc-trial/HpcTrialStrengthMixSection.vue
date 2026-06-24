<script setup lang="ts">
import HpcTrialDataTable from "./HpcTrialDataTable.vue";
import { formatKg, formatNullableNumber } from "../../utils/format";

interface TableColumn {
  key: string;
  label: string;
  width?: number | string;
  minWidth?: number | string;
}

interface TableCell {
  text: string;
  unit?: string;
  changed?: boolean;
  emphasized?: boolean;
  input?: {
    value: number | null;
    onInput: (v: number | null) => void;
    min?: number;
    max?: number;
    step?: number;
    precision?: number;
    placeholder?: string;
  };
}

type TableValue = TableCell | string | number | null | undefined;
type TableRow = Record<string, TableValue>;

interface StrengthMixTableRow {
  headerLabel: string;
  headerType: "primary" | "success" | "danger";
  summary: string;
  rows: TableRow[];
}

const props = defineProps<{
  materialColumns: TableColumn[];
  mixColumns: TableColumn[];
  baseWb: number | null | undefined;
  baseBs: number | null | undefined;
  baseBinder: number | null | undefined;
  baseMaterialRows: TableRow[];
  strengthMixTableRows: StrengthMixTableRow[];
}>();

const fmt = formatNullableNumber;
const fmtKg = formatKg;
</script>

<template>
  <div class="section-title">
    <el-icon color="#2a5298"><List /></el-icon>
    基准配合比（来自工作性实验调整结果）
  </div>
  <div class="formula-row" style="margin-bottom: 8px">
    <span class="formula-label">水胶比 W/B：</span>
    <span class="formula-val">{{ fmt(props.baseWb, 2) }}</span>
    <span class="formula-label" style="margin-left: 20px">砂率 β<sub>s</sub>：</span>
    <span class="formula-val">{{ fmt(props.baseBs) }} %</span>
    <span class="formula-label" style="margin-left: 20px">胶材用量 m<sub>b</sub>：</span>
    <span class="formula-val">{{ fmtKg(props.baseBinder) }}</span>
  </div>

  <HpcTrialDataTable :columns="materialColumns" :rows="baseMaterialRows" />

  <el-divider content-position="left">
    <span style="font-size: 13px; color: #666">三组强度实验配合比</span>
  </el-divider>

  <template
    v-for="(mixTable, index) in props.strengthMixTableRows"
    :key="mixTable.headerLabel + '-' + index"
  >
    <div
      class="strength-mix-header"
      :class="index === 0 ? 'mix-base' : index === 1 ? 'mix-plus' : 'mix-minus'"
    >
      <el-tag :type="mixTable.headerType" size="small" effect="dark">
        {{ mixTable.headerLabel }}
      </el-tag>
      <span style="font-size: 12px; margin-left: 8px; color: #606266">
        {{ mixTable.summary }}
      </span>
    </div>

    <HpcTrialDataTable :columns="mixColumns" :rows="mixTable.rows" />
  </template>
</template>