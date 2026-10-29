<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { ChatDotRound, Calendar, Notebook, Lock, User } from '@element-plus/icons-vue'

import { getErrorMessage } from '@/api/http'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: 'admin',
  password: 'admin123',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入学号或账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const features = [
  { icon: Calendar, title: '查真实课表', desc: '对接教务数据，随时问随时答' },
  { icon: Notebook, title: '按资料作答', desc: '基于你上传的课件，答得有理有据' },
  { icon: ChatDotRound, title: '生成学习计划', desc: '一句话生成计划，并自动保存' },
]

async function submit() {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await auth.login(form.username, form.password)
    ElMessage.success('登录成功，欢迎回来')
    router.replace('/chat')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '登录失败，请检查账号密码'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login">
    <div class="login-wrap">
      <section class="hero rise">
        <div class="brand">
          <div class="logo-mark">C</div>
          <span>Campus Copilot Pro</span>
        </div>

        <h1>
          你的<span class="gradient-text"> AI 课程助手</span>
        </h1>
        <p class="desc">
          查真实课表、按课件作答、把学习计划存下来。<br />
          一个对话，搞定这一学期。
        </p>

        <div class="features">
          <div v-for="item in features" :key="item.title" class="feature glass">
            <el-icon :size="20" class="feature-icon"><component :is="item.icon" /></el-icon>
            <div>
              <strong>{{ item.title }}</strong>
              <p>{{ item.desc }}</p>
            </div>
          </div>
        </div>
      </section>

      <section class="panel glass rise">
        <h2>学生登录</h2>
        <p class="panel-sub">使用学号和密码登录校园系统</p>

        <el-form ref="formRef" :model="form" :rules="rules" size="large" @submit.prevent="submit">
          <el-form-item prop="username">
            <el-input v-model="form.username" :prefix-icon="User" placeholder="学号 / 账号" />
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              show-password
              :prefix-icon="Lock"
              placeholder="密码"
              @keyup.enter="submit"
            />
          </el-form-item>
          <el-button type="primary" class="submit" :loading="loading" @click="submit">
            登录
          </el-button>
        </el-form>

        <p class="tip">初始管理员账号：admin / admin123</p>
      </section>
    </div>
  </div>
</template>

<style scoped>
.login {
  display: grid;
  place-items: center;
  min-height: 100vh;
  padding: 40px 24px;
}

.login-wrap {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 56px;
  align-items: center;
  width: min(1040px, 100%);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 26px;
  font-size: 13px;
  letter-spacing: 1px;
  color: var(--text-muted);
}

.logo-mark {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  font-weight: 800;
  color: #fff;
  border-radius: 10px;
  background: var(--grad);
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.4);
}

h1 {
  margin: 0;
  font-size: 44px;
  line-height: 1.25;
  letter-spacing: 1px;
}

.desc {
  margin: 16px 0 30px;
  font-size: 14px;
  line-height: 1.9;
  color: var(--text-muted);
}

.features {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.feature {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
}

.feature-icon {
  color: #a78bfa;
}

.feature strong {
  font-size: 14px;
}

.feature p {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--text-muted);
}

.panel {
  padding: 36px 32px;
}

.panel h2 {
  margin: 0;
  font-size: 22px;
}

.panel-sub {
  margin: 8px 0 26px;
  font-size: 13px;
  color: var(--text-muted);
}

.submit {
  width: 100%;
  margin-top: 6px;
  letter-spacing: 2px;
}

.tip {
  margin: 18px 0 0;
  font-size: 12px;
  text-align: center;
  color: var(--text-muted);
}

.rise:nth-child(2) {
  animation-delay: 0.1s;
}

@media (max-width: 900px) {
  .login-wrap {
    grid-template-columns: 1fr;
    gap: 32px;
  }

  h1 {
    font-size: 32px;
  }
}
</style>
