<script setup lang="ts">
const deltaWb = defineModel<number>("deltaWb", { required: true });
const deltaBs = defineModel<number>("deltaBs", { required: true });
const strength0 = defineModel<number | null>("strength0", { required: true });
const strengthP = defineModel<number | null>("strengthP", { required: true });
const strengthN = defineModel<number | null>("strengthN", { required: true });
const sTargetStrength = defineModel<number | null>("sTargetStrength", {
  required: true,
});
</script>

<template>
  <el-divider content-position="left">
    <span style="font-size: 13px; color: #666">强度实验调整步长</span>
  </el-divider>
  <p style="font-size: 12px; color: #909399; margin-bottom: 10px">
    以工作性实验确认后的基准配合比为中心进行三组强度实验。调整水胶比时保持胶凝材料总量不变，水 = 胶材 × W/B；调整砂率时保持粗细骨料总量不变。外加剂掺量可由用户自定义输入。
  </p>

  <el-form label-position="top" size="default">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-form-item>
          <template #label>水胶比步长 ΔW/B</template>
          <el-input-number
            v-model="deltaWb"
            :min="0.01"
            :max="0.1"
            :step="0.01"
            :precision="2"
            style="width: 100%"
          />
        </el-form-item>
      </el-col>
      <el-col :span="6">
        <el-form-item>
          <template #label>砂率步长 Δβ<sub>s</sub></template>
          <el-input-number
            v-model="deltaBs"
            :min="0.5"
            :max="10"
            :step="0.5"
            :precision="1"
            style="width: 100%"
          >
            <template #suffix><span class="unit-suffix">%</span></template>
          </el-input-number>
        </el-form-item>
      </el-col>
    </el-row>
  </el-form>

  <el-divider content-position="left">
    <span style="font-size: 13px; color: #666">实测 28d 抗压强度</span>
  </el-divider>

  <el-form label-position="top" size="default">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-form-item>
          <template #label>基准组强度</template>
          <el-input-number
            v-model="strength0"
            :min="0"
            :max="200"
            :step="0.1"
            :precision="1"
            style="width: 100%"
          >
            <template #suffix><span class="unit-suffix">MPa</span></template>
          </el-input-number>
        </el-form-item>
      </el-col>
      <el-col :span="6">
        <el-form-item>
          <template #label>+Δ 组强度</template>
          <el-input-number
            v-model="strengthP"
            :min="0"
            :max="200"
            :step="0.1"
            :precision="1"
            style="width: 100%"
          >
            <template #suffix><span class="unit-suffix">MPa</span></template>
          </el-input-number>
        </el-form-item>
      </el-col>
      <el-col :span="6">
        <el-form-item>
          <template #label>-Δ 组强度</template>
          <el-input-number
            v-model="strengthN"
            :min="0"
            :max="200"
            :step="0.1"
            :precision="1"
            style="width: 100%"
          >
            <template #suffix><span class="unit-suffix">MPa</span></template>
          </el-input-number>
        </el-form-item>
      </el-col>
      <el-col :span="6">
        <el-form-item>
          <template #label>配制强度</template>
          <el-input :model-value="sTargetStrength === null ? '—' : sTargetStrength.toFixed(1)" readonly class="trial-readonly-input">
            <template #suffix><span class="unit-suffix">MPa</span></template>
          </el-input>
        </el-form-item>
      </el-col>
    </el-row>
  </el-form>
</template>