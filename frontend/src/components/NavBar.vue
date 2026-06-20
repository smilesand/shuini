<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { User, ArrowDown } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/authStore'
import { navMenu, filterNavItems } from '../router'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const topNavItems = computed(() => filterNavItems(navMenu, authStore.isAdmin))

async function handleCommand(cmd: string) {
  if (cmd === 'profile') {
    router.push('/profile')
  } else if (cmd === 'activate') {
    router.push('/activation')
  } else if (cmd === 'logout') {
    await authStore.logout()
    await router.push('/login')
  }
}
</script>

<template>
  <header class="navbar">
    <div class="nav-brand">
      <img class="brand-logo" src="../../public/logo.png" alt="混凝土配合比设计系统" />
    </div>
    <nav class="nav-links">
      <RouterLink
        v-for="item in topNavItems"
        :key="item.path"
        :to="item.path"
        :class="{ active: route.path === item.path || route.path.startsWith(item.path + '/') }"
      >{{ item.title }}</RouterLink>
    </nav>
    <div class="nav-right">
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
            <el-dropdown-item command="activate">
              激活软件
            </el-dropdown-item>
            <el-dropdown-item command="logout" divided>
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <RouterLink v-else to="/login" class="login-link">登录</RouterLink>
    </div>
  </header>
</template>

<style scoped>
.navbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 32px; height: 60px;
  background: linear-gradient(135deg, #1e3c72, #2a5298);
  box-shadow: 0 2px 12px rgba(0,0,0,.18);
  position: sticky; top: 0; z-index: 100;
}
.nav-brand {
  display: flex;
  align-items: center;
  height: 100%;
}
.brand-logo {
  display: block;
  height: 100%;
  width: auto;
  object-fit: contain;
}
.nav-links { display: flex; gap: 4px; }
.nav-links a {
  padding: 7px 18px; border-radius: 20px; color: rgba(255,255,255,.8);
  text-decoration: none; font-size: 14px; font-weight: 500; transition: .2s;
}
.nav-links a:hover, .nav-links a.active {
  background: rgba(255,255,255,.18); color: #fff;
}

.nav-right { display: flex; align-items: center; }

.user-dropdown-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 20px;
  color: rgba(255,255,255,.9);
  cursor: pointer;
  font-size: 14px;
  transition: .2s;
  user-select: none;
}
.user-dropdown-trigger:hover {
  background: rgba(255,255,255,.18);
  color: #fff;
}
.username-text { font-weight: 500; }
.arrow-icon { font-size: 12px; transition: .2s; }

.login-link {
  padding: 7px 18px;
  border-radius: 20px;
  color: rgba(255,255,255,.85);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: .2s;
}
.login-link:hover {
  background: rgba(255,255,255,.18);
  color: #fff;
}
</style>
