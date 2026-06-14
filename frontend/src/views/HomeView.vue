<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useCalcStore } from '../stores/calcStore'
import { useUhpcStore } from '../stores/uhpcStore'
import { getProfile } from '../api/auth'
import { listRecords, type RecordItem } from '../api/records'
import { listProjects, type Project } from '../api/projects'

const router = useRouter()
const authStore = useAuthStore()
const calcStore = useCalcStore()
const uhpcStore = useUhpcStore()

const showResetGuide = ref(false)
const loading = ref(true)
const username = ref('')

const totalProjects = ref(0)
const totalHpc = ref(0)
const totalUhpc = ref(0)
const recentRecords = ref<RecordItem[]>([])
const recentProjects = ref<Project[]>([])

const timeGreeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '凌晨好'
  if (h < 11) return '早上好'
  if (h < 13) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const todayLabel = computed(() => {
  const d = new Date()
  const days = ['日', '一', '二', '三', '四', '五', '六']
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日  ·  星期${days[d.getDay()]}`
})

onMounted(async () => {
  loading.value = true
  try {
    const [prof, hpcRes, uhpcRes, projRes, recentRes] =
      await Promise.allSettled([
        getProfile(),
        listRecords({ category: 'hpc', page: 1, page_size: 1 }),
        listRecords({ category: 'uhpc', page: 1, page_size: 1 }),
        listProjects(undefined, 1, 8),
        listRecords({ page: 1, page_size: 10 }),
      ])
    if (prof.status === 'fulfilled') {
      username.value = prof.value.username
      if (prof.value.must_reset) showResetGuide.value = true
    }
    if (hpcRes.status === 'fulfilled') totalHpc.value = hpcRes.value.total
    if (uhpcRes.status === 'fulfilled') totalUhpc.value = uhpcRes.value.total
    if (projRes.status === 'fulfilled') {
      totalProjects.value = projRes.value.total
      recentProjects.value = projRes.value.items
    }
    if (recentRes.status === 'fulfilled')
      recentRecords.value = recentRes.value.items
  } finally {
    loading.value = false
  }
})

const stats = computed(() => [
  {
    label: '项目总数',
    value: totalProjects.value,
    unit: '个',
    icon: 'Folder',
    accent: '#2a5298',
    bg: 'linear-gradient(135deg,#e8f0fb,#d3e3f8)',
  },
  {
    label: 'HPC 计算记录',
    value: totalHpc.value,
    unit: '条',
    icon: 'DataAnalysis',
    accent: '#1565c0',
    bg: 'linear-gradient(135deg,#e3f2fd,#bbdefb)',
  },
  {
    label: 'UHPC 计算记录',
    value: totalUhpc.value,
    unit: '条',
    icon: 'Lightning',
    accent: '#5d4037',
    bg: 'linear-gradient(135deg,#fbe9e7,#ffccbc)',
  },
  {
    label: '试配记录',
    value: totalHpc.value + totalUhpc.value,
    unit: '条',
    icon: 'Document',
    accent: '#2e7d32',
    bg: 'linear-gradient(135deg,#e8f5e9,#c8e6c9)',
  },
])

const quickActions = [
  {
    icon: 'DataAnalysis',
    title: 'HPC 配比计算',
    desc: '高性能混凝土配合比全流程精算',
    path: '/calc/hpc',
    accent: '#2a5298',
    badge: 'HPC',
  },
  {
    icon: 'Lightning',
    title: 'UHPC 配比计算',
    desc: '超高性能混凝土配合比全流程精算',
    path: '/calc/uhpc',
    accent: '#7b1fa2',
    badge: 'UHPC',
  },
  {
    icon: 'Edit',
    title: 'HPC 试配调整',
    desc: '工作性 · 强度 · 校正全流程试配',
    path: '/adapt/hpc',
    accent: '#00695c',
    badge: '试配',
  },
  {
    icon: 'Memo',
    title: 'UHPC 试配调整',
    desc: '超高性能混凝土试配调整',
    path: '/adapt/uhpc',
    accent: '#e65100',
    badge: '试配',
  },
  {
    icon: 'FolderOpened',
    title: '项目管理',
    desc: '新建项目、关联记录、查看汇总',
    path: '/projects',
    accent: '#1565c0',
    badge: '管理',
  },
]

function categoryTag(cat: string): 'primary' | 'warning' {
  return cat === 'uhpc' ? 'warning' : 'primary'
}
function categoryLabel(cat: string) {
  return cat === 'uhpc' ? 'UHPC' : 'HPC'
}
function fmtDate(s: string) {
  return s ? s.replace('T', ' ').slice(0, 16) : '—'
}

function openRecentRecord(record: RecordItem) {
  if (record.category === 'uhpc') {
    uhpcStore.applyRecordData(record)
    router.push({
      path: '/calc/uhpc',
      query: record.project_id ? { project_id: record.project_id } : {},
    })
    return
  }

  calcStore.applyRecordData(record)
  router.push({
    path: '/calc/hpc',
    query: record.project_id ? { project_id: record.project_id } : {},
  })
}
</script>

<template>
  <div class="home-wrap" v-loading="loading">
    <!-- ── 顶部 Banner ── -->
    <div class="hero-banner">
      <div class="hero-bg-grid" aria-hidden="true" />
      <div class="hero-inner">
        <div class="hero-left">
          <div class="hero-system-label">
            <el-icon style="font-size: 11px"><Setting /></el-icon>
            CRRC &middot; Wind Tower Concrete Platform
          </div>
          <!-- <h1 class="hero-system-title">
            中国中车风电混塔用<br />
            <span class="title-accent">高&nbsp;/&nbsp;超高性能</span
            >混凝土<br />配合比设计系统
          </h1> -->
          <div class="hero-meta">
            <span class="hero-greeting"
              >{{ timeGreeting }}，<span class="hero-name">{{
                username || authStore.username
              }}</span></span
            >
            <span class="meta-sep">·</span>
            <span class="hero-date">{{ todayLabel }}</span>
          </div>
        </div>
        <div class="hero-right">
          <el-button class="hero-cta" @click="router.push('/calc/hpc')">
            <el-icon><DataAnalysis /></el-icon>
            开始计算
          </el-button>
          <el-button class="hero-cta-ghost" @click="router.push('/projects')">
            <el-icon><Folder /></el-icon>
            项目管理
          </el-button>
        </div>
      </div>
    </div>

    <!-- 密码重置提示 -->
    <el-alert
      v-if="showResetGuide"
      title="您当前使用默认密码，建议前往「个人中心」修改密码以保障账户安全。"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 20px; border-radius: 10px"
    />

    <!-- ── 统计指标卡 ── -->
    <div class="stats-grid">
      <div
        v-for="s in stats"
        :key="s.label"
        class="stat-card"
        :style="{ '--accent': s.accent, '--card-bg': s.bg }"
      >
        <div class="stat-icon-wrap">
          <el-icon :size="22"><component :is="s.icon" /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-value">
            {{ s.value }}<span class="stat-unit">{{ s.unit }}</span>
          </div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
      </div>
    </div>

    <!-- ── 主内容区 ── -->
    <div class="main-content">
      <!-- 快捷操作 -->
      <div class="section-card actions-section">
        <div class="section-header">
          <el-icon color="#2a5298"><Grid /></el-icon>
          <span>快捷操作</span>
        </div>
        <div class="actions-row-grid">
          <div
            v-for="a in quickActions"
            :key="a.path"
            class="action-card"
            :style="{ '--a-accent': a.accent }"
            @click="router.push(a.path)"
          >
            <div class="action-icon">
              <el-icon :size="24"><component :is="a.icon" /></el-icon>
            </div>
            <div class="action-info">
              <div class="action-title">{{ a.title }}</div>
              <div class="action-desc">{{ a.desc }}</div>
            </div>
            <el-tag class="action-badge" size="small" effect="plain">{{
              a.badge
            }}</el-tag>
          </div>
        </div>
      </div>

      <!-- 下方项目与记录 -->
      <div class="lists-grid">
        <!-- 最近项目 -->
        <div class="section-card list-card">
          <div class="section-header">
            <el-icon color="#357a38"><Folder /></el-icon>
            <span>最近项目</span>
            <el-button
              link
              size="small"
              style="margin-left: auto"
              @click="router.push('/projects')"
            >
              查看全部 <el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>
          <div v-if="recentProjects.length" class="project-list">
            <div
              v-for="p in recentProjects"
              :key="p.id"
              class="project-row"
              @click="router.push(`/projects/${p.id}`)"
            >
              <div class="project-code-badge">{{ p.project_code }}</div>
              <div class="project-meta">
                <div class="project-name">{{ p.project_name }}</div>
                <div class="project-count">{{ p.record_count }} 条记录</div>
              </div>
              <el-icon class="project-arrow"><ArrowRight /></el-icon>
            </div>
          </div>
          <el-empty v-else description="暂无项目" :image-size="48" />
        </div>

        <!-- 最近记录 -->
        <div class="section-card list-card">
          <div class="section-header">
            <el-icon color="#1565c0"><Document /></el-icon>
            <span>最近配合记录</span>
            <el-button
              link
              size="small"
              style="margin-left: auto"
              @click="router.push('/records')"
            >
              查看全部 <el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>
          <div v-if="recentRecords.length" class="record-list">
            <div
              v-for="r in recentRecords"
              :key="r.id"
              class="record-row"
              @click="openRecentRecord(r)"
            >
              <el-tag
                :type="categoryTag(r.category)"
                size="small"
                effect="dark"
                class="record-tag"
              >
                {{ categoryLabel(r.category) }}
              </el-tag>
              <span class="record-name">{{ r.name }}</span>
              <span class="record-date">{{ fmtDate(r.created_at) }}</span>
            </div>
          </div>
          <el-empty v-else description="暂无计算记录" :image-size="48" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ── 整体容器 ── */
.home-wrap {
  padding: 0;
  min-height: calc(100vh - 60px);
}

/* ── Hero Banner ── */
.hero-banner {
  position: relative;
  overflow: hidden;
  background-image:
    linear-gradient(rgba(18, 40, 78, 0.42), rgba(18, 40, 78, 0.42)),
    url('/banner.png');
  background-position: center;
  background-repeat: no-repeat;
  background-size: cover;
  border-radius: 16px;
  margin-bottom: 24px;
  padding: 40px 40px 36px;
  color: #fff;
}

.hero-bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
}

.hero-inner {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 24px;
}

.hero-system-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.75);
  font-size: 11px;
  letter-spacing: 0.18em;
  margin-bottom: 18px;
}

.hero-system-title {
  margin: 0 0 20px;
  font-size: clamp(24px, 3.2vw, 40px);
  font-weight: 800;
  line-height: 1.28;
  letter-spacing: 0.04em;
  color: #fff;
  font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  text-shadow: 0 2px 16px rgba(0, 0, 0, 0.4);
}

.title-accent {
  color: #ffd54f;
  font-style: normal;
}

.hero-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
}

.meta-sep {
  opacity: 0.4;
}

.hero-greeting {
  color: rgba(255, 255, 255, 0.75);
}

.hero-right {
  display: flex;
  gap: 12px;
  flex-shrink: 0;
}

.hero-cta {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.35);
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  border-radius: 8px;
  padding: 10px 22px;
  height: auto;
  transition:
    background 0.2s,
    transform 0.15s;
}
.hero-cta:hover {
  background: rgba(255, 255, 255, 0.25);
  transform: translateY(-1px);
}

.hero-cta-ghost {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.35);
  color: rgba(255, 255, 255, 0.85);
  font-size: 14px;
  border-radius: 8px;
  padding: 10px 22px;
  height: auto;
  transition:
    background 0.2s,
    transform 0.15s;
}
.hero-cta-ghost:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: translateY(-1px);
}

/* ── 统计卡 ── */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

@media (max-width: 1100px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 600px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}

.stat-card {
  background: var(--card-bg, #f5f7fa);
  border-radius: 12px;
  padding: 20px 20px 18px;
  display: flex;
  align-items: center;
  gap: 16px;
  border-left: 4px solid var(--accent, #2a5298);
  transition:
    transform 0.18s,
    box-shadow 0.18s;
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
}

.stat-icon-wrap {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent, #2a5298);
  flex-shrink: 0;
}

.stat-body {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 28px;
  font-weight: 800;
  color: var(--accent, #1e3c72);
  line-height: 1;
  margin-bottom: 4px;
  font-variant-numeric: tabular-nums;
}

.stat-unit {
  font-size: 13px;
  font-weight: 500;
  margin-left: 3px;
  color: var(--accent, #2a5298);
  opacity: 0.7;
}

.stat-label {
  font-size: 12px;
  color: #606266;
  font-weight: 600;
  letter-spacing: 0.02em;
}

/* ── 主内容区布局 ── */
.main-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.lists-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  align-items: start;
}

@media (max-width: 900px) {
  .lists-grid {
    grid-template-columns: 1fr;
  }
}

/* ── 通用区块卡 ── */
.section-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.list-card {
  min-height: 100%;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 14px;
  font-weight: 700;
  color: #1e3c72;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

/* ── 快捷操作 ── */
.actions-section {
  width: 100%;
}

.actions-row-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}

@media (max-width: 1200px) {
  .actions-row-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
@media (max-width: 768px) {
  .actions-row-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 480px) {
  .actions-row-grid {
    grid-template-columns: 1fr;
  }
}

.action-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 18px;
  border-radius: 10px;
  background: #fafbfc;
  border: 1px solid #ebeef5;
  cursor: pointer;
  transition:
    background 0.18s,
    border-color 0.18s,
    transform 0.15s,
    box-shadow 0.18s;
  position: relative;
}
.action-card:hover {
  background: #f0f6ff;
  border-color: var(--a-accent, #2a5298);
  transform: translateY(-3px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.action-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: linear-gradient(
    135deg,
    var(--a-accent, #2a5298),
    color-mix(in srgb, var(--a-accent, #2a5298) 70%, #000)
  );
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.action-info {
  flex: 1;
  min-width: 0;
  width: 100%;
}

.action-title {
  font-size: 15px;
  font-weight: 700;
  color: #1e3c72;
  margin-bottom: 6px;
}

.action-desc {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.action-badge {
  position: absolute;
  top: 16px;
  right: 16px;
  border-color: var(--a-accent, #2a5298);
  color: var(--a-accent, #2a5298);
  background: transparent;
}

/* ── 最近项目列表 ── */
.project-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.project-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f5f7fa;
  cursor: pointer;
  transition:
    background 0.18s,
    transform 0.15s;
}
.project-row:hover {
  background: #e8f0fb;
  transform: translateX(2px);
}

.project-code-badge {
  background: linear-gradient(135deg, #1e3c72, #2a5298);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  border-radius: 6px;
  padding: 3px 8px;
  letter-spacing: 0.05em;
  flex-shrink: 0;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-meta {
  flex: 1;
  min-width: 0;
}

.project-name {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-count {
  font-size: 11px;
  color: #909399;
  margin-top: 2px;
}

.project-arrow {
  color: #c0c4cc;
  flex-shrink: 0;
}

/* ── 最近记录列表 ── */
.record-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.record-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 7px;
  background: #fafbfc;
  border: 1px solid #ebeef5;
  cursor: pointer;
  transition:
    background 0.18s,
    border-color 0.18s,
    transform 0.15s;
}

.record-row:hover {
  background: #f0f6ff;
  border-color: #bfd4f5;
  transform: translateX(2px);
}

.record-tag {
  flex-shrink: 0;
}

.record-name {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-date {
  font-size: 11px;
  color: #909399;
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}
</style>
