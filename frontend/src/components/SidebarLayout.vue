<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/authStore'
import { navMenu, buildPageTitles, type MenuItem } from '../router'

const route     = useRoute()
const router    = useRouter()
const authStore = useAuthStore()

const collapsed = ref(false)

const pageTitles = buildPageTitles(navMenu)
const pageTitle = computed(() => pageTitles[route.path] ?? String(route.meta.title ?? '混凝土配合比设计系统'))

/** 递归渲染菜单项 */
function visibleItems(items: MenuItem[]): MenuItem[] {
  return items.filter(item => !item.adminOnly || authStore.isAdmin)
}

async function handleCommand(cmd: string) {
  if (cmd === 'profile') {
    router.push('/profile')
  } else if (cmd === 'logout') {
    await authStore.logout()
    await router.push('/login')
  }
}
</script>

<template>
  <el-container class="layout-root">
    <!-- ── 左侧边栏 ── -->
    <el-aside :width="collapsed ? '64px' : '220px'" class="layout-aside">
      <div class="aside-brand">
        <!-- 侧栏品牌统一使用 public 目录下的 logo 图片，避免重复维护文字品牌。 -->
        <img class="aside-logo" src="/logo.png" alt="水泥配比计算器" />
      </div>

      <el-scrollbar class="aside-scroll">
        <el-menu
          :default-active="route.path"
          :collapse="collapsed"
          router
          class="sidebar-menu"
          :collapse-transition="false"
        >
          <template v-for="item in visibleItems(navMenu)" :key="item.path">
            <!-- 有子菜单 -->
            <el-sub-menu v-if="item.children && item.children.length" :index="item.path">
              <template #title>
                <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
                <span>{{ item.title }}</span>
              </template>
              <el-menu-item
                v-for="child in item.children"
                :key="child.path"
                :index="child.path"
              >
                <template #title>{{ child.title }}</template>
              </el-menu-item>
            </el-sub-menu>
            <!-- 无子菜单 -->
            <el-menu-item v-else :index="item.path">
              <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
              <template #title>{{ item.title }}</template>
            </el-menu-item>
          </template>
        </el-menu>
      </el-scrollbar>

      <div class="aside-footer">
        <el-button text class="collapse-btn" @click="collapsed = !collapsed">
          <el-icon :size="18">
            <component :is="collapsed ? 'ArrowRight' : 'ArrowLeft'" />
          </el-icon>
        </el-button>
      </div>
    </el-aside>

    <!-- ── 右侧主体 ── -->
    <el-container direction="vertical" class="layout-body">
      <el-header class="layout-header" height="60px">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">混凝土配合比设计</el-breadcrumb-item>
            <el-breadcrumb-item>{{ pageTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-dropdown v-if="authStore.isLoggedIn" trigger="click" @command="handleCommand">
            <span class="user-dropdown-trigger">
              <el-icon><User /></el-icon>
              <span class="username-text">{{ authStore.username }}</span>
              <el-icon class="arrow-icon"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>
                  个人中心
                </el-dropdown-item>
                <el-dropdown-item command="logout" divided>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <RouterLink v-else to="/login" class="login-link">登录</RouterLink>
        </div>
      </el-header>

      <el-main class="layout-content">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout-root {
  height: 100vh;
  overflow: hidden;
}

/* ── 侧边栏 ── */
.layout-aside {
  background: linear-gradient(180deg, #1e3c72 0%, #2a5298 100%);
  display: flex;
  flex-direction: column;
  transition: width 0.25s ease;
  overflow: hidden;
}

.aside-brand {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  height: 60px;
  min-height: 60px;
  white-space: nowrap;
  overflow: hidden;
}
.aside-logo {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background-color: rgba(255, 255, 255, 1);
}

.aside-scroll { flex: 1; overflow: hidden; }

/* Element Plus el-menu overrides for dark sidebar */
.sidebar-menu {
  --el-menu-bg-color: transparent;
  --el-menu-text-color: rgba(255, 255, 255, 0.72);
  --el-menu-active-color: #ffffff;
  --el-menu-hover-bg-color: rgba(255, 255, 255, 0.12);
  --el-menu-item-height: 50px;
  border-right: none !important;
  background: transparent !important;
}
.sidebar-menu :deep(.el-menu-item.is-active) {
  background-color: rgba(255, 255, 255, 0.2) !important;
  font-weight: 600;
}
.sidebar-menu :deep(.el-menu-item):hover {
  background-color: rgba(255, 255, 255, 0.12) !important;
}
.sidebar-menu :deep(.el-menu--collapse) {
  width: 64px;
}

.aside-footer {
  padding: 10px 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.12);
  display: flex;
  justify-content: flex-end;
}
.collapse-btn { color: rgba(255, 255, 255, 0.72) !important; }
.collapse-btn:hover { color: #fff !important; }

/* ── 右侧主体 ── */
.layout-body {
  overflow: hidden;
}

.layout-header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid #e8eaec;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.header-left { display: flex; align-items: center; }
.header-right { display: flex; align-items: center; }

.user-dropdown-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 20px;
  color: #606266;
  cursor: pointer;
  font-size: 14px;
  transition: .2s;
  user-select: none;
}
.user-dropdown-trigger:hover {
  background: #f0f2f5;
}
.username-text { font-weight: 500; }
.arrow-icon { font-size: 12px; transition: .2s; }

.login-link {
  padding: 7px 18px;
  border-radius: 20px;
  color: #606266;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: .2s;
}
.login-link:hover { background: #f0f2f5; }

.layout-content {
  flex: 1;
  background: #f0f2f5;
  overflow-y: auto;
  padding: 16px;
}
</style>
