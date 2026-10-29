<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Clock, Delete, Plus } from '@element-plus/icons-vue'

import { getErrorMessage } from '@/api/http'
import type { StudyPlan, StudyPlanTask } from '@/api/studyPlans'
import { useStudyPlanStore } from '@/stores/studyPlan'

const store = useStudyPlanStore()

// 正在提交的任务，提交期间禁用该复选框，避免快速连点导致请求乱序
const pendingTasks = ref<Set<number>>(new Set())

onMounted(async () => {
  try {
    await store.load()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '学习计划加载失败'))
  }
})

function progressOf(tasks: StudyPlanTask[]) {
  if (tasks.length === 0) return 0
  const done = tasks.filter((task) => task.done).length
  return Math.round((done / tasks.length) * 100)
}

async function toggleTask(plan: StudyPlan, task: StudyPlanTask, value: unknown) {
  const done = Boolean(value)
  const previous = task.done

  task.done = done
  pendingTasks.value.add(task.id)
  try {
    await store.setTaskDone(plan.id, task.id, done)
  } catch (error) {
    task.done = previous
    ElMessage.error(getErrorMessage(error, '任务状态保存失败'))
  } finally {
    pendingTasks.value.delete(task.id)
  }
}

async function removePlan(plan: StudyPlan) {
  try {
    await ElMessageBox.confirm(`确定删除「${plan.title}」吗？`, '删除计划', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }

  try {
    await store.remove(plan.id)
    ElMessage.success('计划已删除')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '删除失败'))
  }
}

function askAssistant() {
  ElMessage.info('在「AI 助手」里说一句“帮我规划学习计划”，确认信息后会自动保存到这里')
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">学习计划</h1>
        <p class="page-sub">助手确认后生成的计划会保存在这里，勾选即可记录进度，过期自动清理</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="askAssistant">生成新计划</el-button>
    </div>

    <div v-loading="store.loading" class="plan-grid">
      <div v-if="!store.loading && store.plans.length === 0" class="empty-plan glass rise">
        <p>还没有学习计划</p>
        <span>去「AI 助手」说“帮我规划学习计划”，把课程和截止时间告诉学姐，确认后就会出现在这里</span>
      </div>

      <article v-for="plan in store.plans" :key="plan.id" class="plan glass rise">
        <header class="plan-head">
          <div>
            <h3>{{ plan.title }}</h3>
            <p class="meta">
              <el-tag size="small" effect="plain" round>{{ plan.course ?? '未填课程' }}</el-tag>
              <span class="deadline">
                <el-icon :size="12"><Clock /></el-icon>
                {{ plan.deadline ?? '未设置' }} 截止
              </span>
            </p>
          </div>
          <div class="head-right">
            <strong class="percent">{{ progressOf(plan.tasks) }}%</strong>
            <el-button
              text
              circle
              :icon="Delete"
              title="删除计划"
              @click="removePlan(plan)"
            />
          </div>
        </header>

        <el-progress
          :percentage="progressOf(plan.tasks)"
          :show-text="false"
          :stroke-width="8"
          class="bar"
        />

        <ul class="tasks">
          <li v-for="task in plan.tasks" :key="task.id">
            <el-checkbox
              :model-value="task.done"
              :disabled="pendingTasks.has(task.id)"
              @change="toggleTask(plan, task, $event)"
            >
              {{ task.name }}
            </el-checkbox>
          </li>
        </ul>
      </article>
    </div>
  </div>
</template>

<style scoped>
.plan-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  align-content: start;
  overflow: auto;
}

.empty-plan {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 48px 24px;
  text-align: center;
}

.empty-plan p {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.empty-plan span {
  max-width: 420px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-muted);
}

.plan {
  min-width: 0;
  padding: 20px;
  transition: transform 0.22s ease, border-color 0.22s ease;
}

.plan:hover {
  transform: translateY(-4px);
  border-color: rgba(167, 139, 250, 0.45);
}

.plan-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.plan-head > div:first-child {
  min-width: 0;
}

.plan-head h3 {
  margin: 0;
  font-size: 16px;
  overflow-wrap: anywhere;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin: 10px 0 0;
}

.deadline {
  display: inline-flex;
  gap: 4px;
  align-items: center;
  font-size: 12px;
  color: var(--text-muted);
}

.head-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.percent {
  font-size: 20px;
  font-weight: 700;
  background: var(--grad);
  background-clip: text;
  -webkit-background-clip: text;
  color: transparent;
}

.bar {
  margin: 16px 0 4px;
}

.tasks {
  margin: 6px 0 0;
  padding: 0;
  list-style: none;
}

.tasks li {
  min-width: 0;
  padding: 5px 0;
  font-size: 13px;
}

/* Element Plus 默认 nowrap，长任务名会顶出卡片，这里强制换行 */
.tasks :deep(.el-checkbox) {
  width: 100%;
  height: auto;
  min-height: 22px;
  margin-right: 0;
  align-items: flex-start;
  white-space: normal;
}

.tasks :deep(.el-checkbox__input) {
  flex-shrink: 0;
  margin-top: 2px;
}

.tasks :deep(.el-checkbox__label) {
  flex: 1;
  min-width: 0;
  padding-left: 8px;
  font-size: 13px;
  line-height: 1.6;
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: break-word;
  color: var(--text-main);
}

.tasks :deep(.el-checkbox.is-checked .el-checkbox__label) {
  color: var(--text-muted);
  text-decoration: line-through;
}
</style>
