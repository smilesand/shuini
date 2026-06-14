<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '../stores/authStore'
import { login } from '../api/auth'

const router    = useRouter()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const form    = reactive({ username: '', password: '' })
const loading = ref(false)

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码',   trigger: 'blur' }],
}

onMounted(() => {
  document.title = '中国中车风电塔混凝土设计系统'
})

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const res = await login(form.username, form.password)
    authStore.setAuth(res.access_token, res.username, res.is_admin)
    if (res.must_reset) {
      ElMessage.info('建议您在个人中心中修改默认密码')
    }
    router.push('/')
  } catch (e: unknown) {
    const msg = (e instanceof Error) ? e.message : '登录失败，请检查用户名和密码'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <!-- 全屏背景 -->
    <div class="bg-layer" aria-hidden="true">
      <img class="bg-img" src="/bg.png" alt="" />
      <div class="bg-overlay" />
      <div class="bg-vignette" />
    </div>

    <!-- 顶部标识条 -->
    <header class="top-bar">
      <div class="top-logo">
        <span class="logo-mark">CRRC</span>
        <span class="logo-sep" />
        <span class="logo-sub">中国中车股份有限公司</span>
      </div>
      <div class="top-right">
        <span class="top-tag">Wind Tower Concrete</span>
      </div>
    </header>

    <!-- 中心主区 -->
    <main class="center-stage">
      <!-- 标题区 -->
      <div class="stage-heading">
        <h1 class="main-title">中国中车风电混塔用混凝土配合比设计系统</h1>
        <p class="main-en">Wind Tower Concrete Mix Design Platform</p>
      </div>

      <!-- 登录卡 -->
      <div class="login-card">
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          size="large"
          class="login-form"
          @submit.prevent="handleLogin"
        >
          <el-form-item prop="username">
            <template #label>
              <span class="field-label">用户名</span>
            </template>
            <el-input
              v-model="form.username"
              placeholder="请输入用户名"
              autocomplete="username"
              autofocus
              :prefix-icon="'User'"
            />
          </el-form-item>
          <el-form-item prop="password">
            <template #label>
              <span class="field-label">密码</span>
            </template>
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              autocomplete="current-password"
              show-password
              :prefix-icon="'Lock'"
            />
          </el-form-item>

          <el-button
            type="primary"
            native-type="submit"
            :loading="loading"
            class="login-btn"
            size="large"
          >
            <span class="btn-text">登 录</span>
            <span class="btn-arrow" aria-hidden="true">→</span>
          </el-button>
        </el-form>
      </div>
    </main>

    <!-- 底部版权 -->
    <footer class="page-footer">
      <span>© 2026 中国中车股份有限公司 · 版权所有</span>
    </footer>
  </div>
</template>

<style scoped>
/* ── 全局变量 ─────────────────────────────────────── */
.login-page {
  --c-gold: #d4a843;
  --c-gold-dim: rgba(212, 168, 67, 0.6);
  --c-sky: #2e86c9;
  --c-sky-dim: rgba(46, 134, 201, 0.35);
  --c-white: #ffffff;
  --c-white-80: rgba(255, 255, 255, 0.80);
  --c-white-50: rgba(255, 255, 255, 0.50);
  --c-white-12: rgba(255, 255, 255, 0.12);
  --c-dark: rgba(4, 16, 30, 0.72);
}

/* ── 页面外壳 ─────────────────────────────────────── */
.login-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow: hidden;
  font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* ── 背景层 ───────────────────────────────────────── */
.bg-layer {
  position: fixed;
  inset: 0;
  z-index: 0;
}

.bg-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center 30%;
  transform: scale(1.04);
}

.bg-overlay {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(to bottom,
      rgba(4, 16, 34, 0.38) 0%,
      rgba(5, 22, 45, 0.55) 40%,
      rgba(3, 14, 30, 0.82) 100%);
}

.bg-vignette {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 120% 90% at 50% 110%,
      rgba(0, 10, 24, 0.68) 0%,
      transparent 60%),
    radial-gradient(ellipse 70% 40% at 50% -10%,
      rgba(0, 10, 20, 0.30) 0%,
      transparent 55%);
}

/* ── 顶部标识条 ───────────────────────────────────── */
.top-bar {
  position: relative;
  z-index: 10;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 40px;
  border-bottom: 1px solid var(--c-white-12);
  animation: fadeDown 0.7s ease both;
}

.top-logo {
  display: flex;
  align-items: center;
  gap: 14px;
}

.logo-mark {
  font-size: 15px;
  font-weight: 900;
  letter-spacing: 0.28em;
  color: var(--c-gold);
}

.logo-sep {
  display: block;
  width: 1px;
  height: 16px;
  background: var(--c-white-50);
}

.logo-sub {
  font-size: 13px;
  color: var(--c-white-80);
  letter-spacing: 0.05em;
}

.top-right {
  display: flex;
  align-items: center;
}

.top-tag {
  padding: 5px 14px;
  border-radius: 999px;
  border: 1px solid var(--c-white-12);
  background: var(--c-white-12);
  color: var(--c-white-80);
  font-size: 11px;
  letter-spacing: 0.15em;
}

/* ── 中心主区 ─────────────────────────────────────── */
.center-stage {
  position: relative;
  z-index: 10;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 36px;
  padding: 40px 20px;
  width: 100%;
  max-width: 600px;
}

/* ── 标题区 ───────────────────────────────────────── */
.stage-heading {
  text-align: center;
  animation: fadeDown 0.8s 0.1s ease both;
}

.deco-line {
  display: block;
  width: 60px;
  height: 1px;
  background: linear-gradient(to right, transparent, var(--c-gold-dim));
}

.deco-line:last-child {
  background: linear-gradient(to left, transparent, var(--c-gold-dim));
}

.deco-dot {
  display: block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--c-gold);
  box-shadow: 0 0 8px 2px rgba(212, 168, 67, 0.5);
}

.main-title {
  margin: 0 0 12px;
  color: var(--c-white);
  font-size: clamp(26px, 4.5vw, 44px);
  font-weight: 700;
  letter-spacing: 0.1em;
  font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  text-shadow:
    0 2px 24px rgba(0, 0, 0, 0.6),
    0 0 80px rgba(46, 134, 201, 0.15);
  line-height: 1.25;
}

.main-en {
  margin: 0;
  color: var(--c-white-50);
  font-size: 13px;
  letter-spacing: 0.22em;
}

/* ── 登录卡 ───────────────────────────────────────── */
.login-card {
  width: 100%;
  padding: 36px 38px 34px;
  border-radius: 24px;
  background: rgba(8, 24, 44, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.14);
  box-shadow:
    0 32px 64px rgba(0, 0, 0, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(24px) saturate(1.3);
  animation: fadeUp 0.8s 0.2s ease both;
}

.card-header {
  margin-bottom: 28px;
}

.card-eyebrow {
  display: inline-block;
  margin-bottom: 8px;
  color: var(--c-gold);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.24em;
}

.card-hint {
  margin: 0;
  color: var(--c-white-50);
  font-size: 14px;
  line-height: 1.6;
}

/* ── 表单 ─────────────────────────────────────────── */
.login-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.field-label {
  color: rgba(255, 255, 255, 0.75);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.05em;
}

.login-form :deep(.el-form-item__label) {
  height: auto;
  line-height: 1;
  padding-bottom: 8px;
}

.login-form :deep(.el-input__wrapper) {
  min-height: 50px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.07);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.12) inset;
  transition: box-shadow 0.22s ease;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1.5px var(--c-sky) inset,
              0 0 0 4px var(--c-sky-dim);
}

.login-form :deep(.el-input__inner) {
  color: var(--c-white);
  font-size: 15px;
}

.login-form :deep(.el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.3);
}

.login-form :deep(.el-input__prefix-inner .el-icon),
.login-form :deep(.el-input__suffix-inner .el-icon) {
  color: rgba(255, 255, 255, 0.4);
}

.login-form :deep(.el-form-item__error) {
  color: #f0a37d;
}

/* ── 登录按钮 ─────────────────────────────────────── */
.login-btn {
  position: relative;
  width: 100%;
  min-height: 52px;
  margin-top: 8px;
  overflow: hidden;
  border: none;
  border-radius: 16px;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.2em;
  background: linear-gradient(100deg, #1660a8 0%, #2e86c9 55%, #3a9bd4 100%);
  box-shadow: 0 12px 28px rgba(46, 134, 201, 0.35);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.login-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(100deg, transparent 0%, rgba(255,255,255,0.18) 50%, transparent 100%);
  transform: translateX(-100%);
  transition: transform 0.5s ease;
}

.login-btn:hover::before {
  transform: translateX(100%);
}

.login-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 36px rgba(46, 134, 201, 0.45);
}

.btn-text {
  color: #fff;
}

.btn-arrow {
  color: rgba(255, 255, 255, 0.65);
  font-size: 16px;
  transition: transform 0.25s ease;
}

.login-btn:hover .btn-arrow {
  transform: translateX(4px);
}

/* ── 底部 ─────────────────────────────────────────── */
.page-footer {
  position: relative;
  z-index: 10;
  width: 100%;
  padding: 18px 40px;
  text-align: center;
  color: rgba(255, 255, 255, 0.3);
  font-size: 12px;
  letter-spacing: 0.05em;
  border-top: 1px solid var(--c-white-12);
  animation: fadeDown 0.7s 0.3s ease both;
}

/* ── 入场动画 ─────────────────────────────────────── */
@keyframes fadeDown {
  from { opacity: 0; transform: translateY(-18px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(24px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── 响应式 ───────────────────────────────────────── */
@media (max-width: 640px) {
  .top-bar { padding: 16px 20px; }
  .top-right { display: none; }
  .logo-sub { display: none; }
  .center-stage { padding: 28px 16px; gap: 24px; }
  .login-card { padding: 26px 22px 24px; border-radius: 20px; }
  .main-title { font-size: 24px; }
  .page-footer { padding: 14px 20px; }
}
</style>
