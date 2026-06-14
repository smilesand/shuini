<template>
  <div class="about-page">
    <el-card :body-style="{ padding: '36px' }" style="border-radius:12px">
      <template #header>
        <div style="display:flex;align-items:center;gap:10px">
          <el-icon color="#2a5298" :size="20"><InfoFilled /></el-icon>
          <span style="font-size:18px;font-weight:700;color:#1e3c72">关于本项目</span>
        </div>
      </template>

      <p class="about-intro">
        本工具基于《超高性能混凝土（UHPC）配合比设计》相关规程，
        实现配比全流程数字化计算。
      </p>

      <el-divider />

      <h3 class="section-title">技术栈</h3>
      <el-descriptions :column="1" border size="small" class="desc-table">
        <el-descriptions-item label="前端框架">Vue 3 + Vite + TypeScript</el-descriptions-item>
        <el-descriptions-item label="UI 组件">Element Plus（企业级）</el-descriptions-item>
        <el-descriptions-item label="状态管理">Pinia（响应式 Store）</el-descriptions-item>
        <el-descriptions-item label="后端框架">Python 3 + FastAPI</el-descriptions-item>
        <el-descriptions-item label="科学计算">NumPy / SciPy（回归拟合）</el-descriptions-item>
        <el-descriptions-item label="API 通信">Axios（RESTful JSON）</el-descriptions-item>
      </el-descriptions>

      <el-divider />

      <h3 class="section-title">计算流程</h3>
      <el-steps direction="vertical" :active="5" :space="60" class="calc-steps">
        <el-step title="水胶比（W/B）" description="鲍罗米公式，支持回归系数导入拟合" />
        <el-step title="砂率（βs）"    description="参考标准砂率表，手动查表并确认" />
        <el-step title="骨料用量"      description="体积法计算粗骨料 mg 与细骨料 ms" />
        <el-step title="胶凝材料"      description="浆体体积法，支持四种掺合料配比" />
        <el-step title="用水量与外加剂" description="由 mb × W/B 得用水量，掺量比得外加剂量" />
      </el-steps>
    </el-card>
  </div>
</template>

<style scoped>
.about-page { width: 100%; }
.about-intro { font-size: 14px; color: #555; line-height: 1.9; margin-bottom: 4px; }
.section-title { font-size: 15px; font-weight: 700; color: #2a5298; margin: 0 0 16px; }
.desc-table { margin-bottom: 4px; }
.calc-steps { margin-top: 8px; }
</style>
