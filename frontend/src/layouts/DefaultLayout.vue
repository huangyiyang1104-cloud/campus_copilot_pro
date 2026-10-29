<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'
import {
  Calendar,
  ChatDotRound,
  FolderOpened,
  Notebook,
  SwitchButton,
  UserFilled,
} from '@element-plus/icons-vue'

import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const navItems = [
  { name: 'chat', path: '/chat', label: 'AI 助手', icon: ChatDotRound },
  { name: 'schedule', path: '/schedule', label: '我的课表', icon: Calendar },
  { name: 'plan', path: '/plan', label: '学习计划', icon: Notebook },
  { name: 'materials', path: '/materials', label: '课程资料', icon: FolderOpened },
  { name: 'users', path: '/users', label: '用户管理', icon: UserFilled, adminOnly: true },
]

// 普通学生看不到用户管理
const visibleNav = computed(() => navItems.filter((item) => !item.adminOnly || auth.isAdmin))

const activeName = computed(() => route.name)

async function logout() {
  await auth.logout()
  router.replace('/login')
}
</script>

<template>
  <div class="layout">
    <aside class="sidebar glass">
      <div class="logo">
        <div class="logo-mark">C</div>
        <div class="logo-text">
          <strong>Campus Copilot</strong>
          <span>AI 课程助手</span>
        </div>
      </div>

      <nav class="nav">
        <RouterLink
          v-for="item in visibleNav"
          :key="item.name"
          :to="item.path"
          class="nav-item"
          :class="{ active: activeName === item.name }"
        >
          <el-icon :size="18"><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="user-card">
        <el-avatar :size="36" class="avatar">{{ auth.user?.name?.[0] ?? '学' }}</el-avatar>
        <div class="user-info">
          <strong>{{ auth.user?.name ?? '同学' }}</strong>
          <span>{{ auth.user?.username ?? '未登录' }}</span>
        </div>
        <el-button text circle :icon="SwitchButton" title="退出登录" @click="logout" />
      </div>
    </aside>

    <main class="main">
      <RouterView v-slot="{ Component }">
        <transition name="fade-slide" mode="out-in">
          <component :is="Component" />
        </transition>
      </RouterView>
    </main>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  gap: 20px;
  height: 100vh;
  padding: 18px;
}

.sidebar {
  display: flex;
  flex-direction: column;
  width: 232px;
  padding: 22px 16px;
  flex-shrink: 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 6px 22px;
}

.logo-mark {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  font-size: 18px;
  font-weight: 800;
  color: #fff;
  border-radius: 12px;
  background: var(--grad);
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.35);
}

.logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.logo-text strong {
  font-size: 14px;
  letter-spacing: 0.4px;
}

.logo-text span {
  font-size: 11px;
  color: var(--text-muted);
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  font-size: 14px;
  color: var(--text-muted);
  text-decoration: none;
  border-radius: 12px;
  transition: all 0.22s ease;
}

.nav-item:hover {
  color: var(--text-main);
  background: rgba(255, 255, 255, 0.05);
}

.nav-item.active {
  color: #fff;
  background: var(--grad);
  box-shadow: 0 10px 24px rgba(124, 58, 237, 0.32);
}

.user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 16px;
  padding: 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
}

.avatar {
  background: var(--grad);
  font-weight: 600;
}

.user-info {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  line-height: 1.35;
}

.user-info strong {
  font-size: 13px;
}

.user-info span {
  font-size: 11px;
  color: var(--text-muted);
}

.main {
  flex: 1;
  min-width: 0;
  min-height: 0;
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.25s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
