import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/chat',
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/ChatView.vue'),
    meta: { title: '智能对话', icon: 'ChatDotRound' },
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: '系统监控', icon: 'Monitor' },
  },
  {
    path: '/tools',
    name: 'Tools',
    component: () => import('@/views/ToolsView.vue'),
    meta: { title: '运维工具', icon: 'SetUp' },
  },
  {
    path: '/safety',
    name: 'Safety',
    component: () => import('@/views/SafetyView.vue'),
    meta: { title: '安全护栏', icon: 'Shield' },
  },
  {
    path: '/traces',
    name: 'Traces',
    component: () => import('@/views/TracesView.vue'),
    meta: { title: '推理溯源', icon: 'List' },
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('@/views/HistoryView.vue'),
    meta: { title: '对话历史', icon: 'Clock' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
