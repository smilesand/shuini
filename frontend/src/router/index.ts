import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const HomeView = () => import('../views/HomeView.vue')
const HpcView = () => import('../views/HpcView.vue')
const AdaptView = () => import('../views/AdaptView.vue')
const TrialUhpcView = () => import('../views/TrialUhpcView.vue')
const ProjectsView = () => import('../views/ProjectsView.vue')
const ProjectDetailView = () => import('../views/ProjectDetailView.vue')
const RecordsView = () => import('../views/RecordsView.vue')
const RecycleBinView = () => import('../views/RecycleBinView.vue')
const CalcIndexView = () => import('../views/CalcIndexView.vue')
const UhpcView = () => import('../views/UhpcView.vue')
const AboutView = () => import('../views/AboutView.vue')
const LoginView = () => import('../views/LoginView.vue')
const SettingsView = () => import('../views/SettingsView.vue')
const ProfileView = () => import('../views/ProfileView.vue')
const ReportView = () => import('../views/ReportView.vue')

// ── 菜单配置（集中管理，供 NavBar / Sidebar 共用）──────────────────────────
export interface MenuItem {
  path: string
  title: string
  icon?: string
  adminOnly?: boolean
  children?: MenuItem[]
  hideInNav?: boolean   // 不在顶部导航栏显示
}

export const navMenu: MenuItem[] = [
  { path: '/',     title: '首页',     icon: 'House' },
  { path: '/projects', title: '项目管理', icon: 'Folder' },
  {
    path: '/calc', title: '配比计算', icon: 'DataAnalysis',
    children: [
      { path: '/calc/hpc',  title: '高性能混凝土' },
      { path: '/calc/uhpc', title: '超高性能混凝土' },
    ],
  },
  {
    path: '/adapt', title: '试配调整', icon: 'Edit',
    children: [
      { path: '/adapt/hpc', title: '高性能试配' },
      { path: '/adapt/uhpc', title: '超高性能试配' },
    ],
  },
  { path: '/report', title: '配合比记录', icon: 'Document' },
  { path: '/recycle-bin', title: '回收站', icon: 'Delete' },
  {
    path: '/settings', title: '系统设置', icon: 'Setting', adminOnly: true,
    children: [
      { path: '/settings/users', title: '用户管理' },
    ],
  },
]

/** 从菜单配置中提取 path → title 映射（用于面包屑） */
export function buildPageTitles(menu: MenuItem[]): Record<string, string> {
  const map: Record<string, string> = {}
  function walk(items: MenuItem[]) {
    for (const item of items) {
      map[item.path] = item.title
      if (item.children) walk(item.children)
    }
  }
  walk(menu)
  return map
}

/** 筛选可在顶部导航栏显示的菜单项（不含 adminOnly，不含 hideInNav） */
export function filterNavItems(menu: MenuItem[], isAdmin: boolean): MenuItem[] {
  return menu.filter(item => !item.adminOnly || isAdmin).filter(item => !item.hideInNav)
}

const routes: RouteRecordRaw[] = [
  { path: '/login',    name: 'login',    component: LoginView,    meta: { public: true } },
  { path: '/',         name: 'home',     component: HomeView },
  {
    path: '/calc',
    component: CalcIndexView,
    children: [
      { path: '',       redirect: '/calc/hpc' },
      { path: 'hpc',   name: 'calc-hpc',  component: HpcView  },
      { path: 'uhpc',  name: 'calc-uhpc', component: UhpcView },
    ],
  },
  { path: '/profile',  name: 'profile',    component: ProfileView },
  { path: '/projects', name: 'projects',   component: ProjectsView },
  { path: '/projects/:id', name: 'project-detail', component: ProjectDetailView, meta: { title: '项目详情' } },
  { path: '/records', name: 'records', component: RecordsView, meta: { title: '配合记录' } },
  { path: '/adapt', redirect: '/adapt/hpc' },
  { path: '/adapt/hpc', name: 'adapt-hpc', component: AdaptView },
  { path: '/adapt/uhpc', name: 'adapt-uhpc', component: TrialUhpcView },
  { path: '/settings', redirect: '/settings/users', meta: { requiresAdmin: true } },
  { path: '/settings/users', name: 'settings-users', component: SettingsView, meta: { requiresAdmin: true } },
  { path: '/about',    name: 'about',    component: AboutView },
  { path: '/report', name: 'report', component: ReportView, meta: { title: '配合比记录' } },
  { path: '/recycle-bin', name: 'recycle-bin', component: RecycleBinView, meta: { title: '回收站' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const token = localStorage.getItem('sc_token')
  const isAdmin = localStorage.getItem('sc_admin') === '1'
  if (!to.meta['public'] && !token) {
    return { name: 'login' }
  }
  if (to.meta['requiresAdmin'] && !isAdmin) {
    return { name: 'home' }
  }
})

export default router
