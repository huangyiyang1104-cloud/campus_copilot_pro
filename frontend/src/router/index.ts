import { createRouter, createWebHistory } from 'vue-router'

import { getCachedUser, getToken } from '@/api/token'
import DefaultLayout from '@/layouts/DefaultLayout.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { title: '登录' },
    },
    {
      path: '/',
      component: DefaultLayout,
      redirect: '/chat',
      meta: { requiresAuth: true },
      children: [
        {
          path: 'chat',
          name: 'chat',
          component: () => import('@/views/ChatView.vue'),
          meta: { title: 'AI 助手' },
        },
        {
          path: 'schedule',
          name: 'schedule',
          component: () => import('@/views/ScheduleView.vue'),
          meta: { title: '我的课表' },
        },
        {
          path: 'plan',
          name: 'plan',
          component: () => import('@/views/PlanView.vue'),
          meta: { title: '学习计划' },
        },
        {
          path: 'materials',
          name: 'materials',
          component: () => import('@/views/MaterialsView.vue'),
          meta: { title: '课程资料' },
        },
        {
          path: 'users',
          name: 'users',
          component: () => import('@/views/UserListView.vue'),
          meta: { title: '用户管理', requiresAdmin: true },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/chat',
    },
  ],
})

/**
 * 全局路由守卫：只判断本地有没有 AT（存在性），
 * AT 是否有效由后端接口决定，失效后由 axios 拦截器刷新。
 */
router.beforeEach((to) => {
  const logged = Boolean(getToken())

  if (to.meta.requiresAuth && !logged) {
    return { name: 'login' }
  }
  if (to.name === 'login' && logged) {
    return { name: 'chat' }
  }
  if (to.meta.requiresAdmin) {
    const user = getCachedUser<{ role?: string }>()
    if (!user || user.role !== 'admin') {
      return { name: 'chat' }
    }
  }
})

router.afterEach((to) => {
  const title = to.meta.title as string | undefined
  document.title = title ? `${title} · Campus Copilot Pro` : 'Campus Copilot Pro'
})

export default router
