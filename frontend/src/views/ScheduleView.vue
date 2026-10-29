<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Delete, Plus, Upload } from '@element-plus/icons-vue'

import { getErrorMessage } from '@/api/http'
import { sections, weekdays, type Course } from '@/mock/data'
import { useScheduleStore } from '@/stores/schedule'
import { parseScheduleFile } from '@/utils/scheduleImport'

const store = useScheduleStore()

// grid[节次][星期] = 课程
const grid = computed(() =>
  sections.map((_, sectionIndex) =>
    weekdays.map((_, dayIndex) =>
      store.courses.find(
        (course) => course.section === sectionIndex + 1 && course.day === dayIndex + 1,
      ),
    ),
  ),
)

// 今天是周几（0 表示周末，不高亮）
const today = computed(() => {
  const day = new Date().getDay()
  return day >= 1 && day <= 5 ? day - 1 : -1
})

const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const fileInput = ref<HTMLInputElement | null>(null)

const form = reactive({
  name: '',
  day: 1,
  section: 1,
  teacher: '',
  room: '',
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入课程名称', trigger: 'blur' }],
  day: [{ required: true, message: '请选择星期', trigger: 'change' }],
  section: [{ required: true, message: '请选择节次', trigger: 'change' }],
}

onMounted(async () => {
  try {
    await store.load()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '课表加载失败'))
  }
})

function openCreate(day = 1, section = 1) {
  editingId.value = null
  Object.assign(form, { name: '', day, section, teacher: '', room: '' })
  dialogVisible.value = true
}

function openEdit(course: Course) {
  editingId.value = course.id
  Object.assign(form, {
    name: course.name,
    day: course.day,
    section: course.section,
    teacher: course.teacher,
    room: course.room,
  })
  dialogVisible.value = true
}

async function submit() {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  const conflict = store.courses.find(
    (course) =>
      course.id !== editingId.value && course.day === form.day && course.section === form.section,
  )
  if (conflict) {
    ElMessage.warning(`这个时段已经有「${conflict.name}」了`)
    return
  }

  const payload = {
    name: form.name.trim(),
    teacher: form.teacher.trim(),
    room: form.room.trim(),
    day: form.day,
    section: form.section,
  }

  try {
    if (editingId.value === null) {
      await store.add(payload)
      ElMessage.success('课程已添加')
    } else {
      await store.update(editingId.value, payload)
      ElMessage.success('课程已保存')
    }
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '课程保存失败'))
    return
  }

  dialogVisible.value = false
}

async function removeCourse() {
  if (editingId.value === null) return

  try {
    await ElMessageBox.confirm('确定删除这门课吗？', '删除课程', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }

  try {
    await store.remove(editingId.value)
    ElMessage.success('已删除')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '删除失败'))
    return
  }

  dialogVisible.value = false
}

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // 允许重复选择同一个文件
  if (!file) return

  const parsed = await parseScheduleFile(file).catch((error: unknown) => {
    ElMessage.error(error instanceof Error ? error.message : '课表文件解析失败')
    return null
  })
  if (!parsed) return

  const { courses, skipped } = parsed
  if (!courses.length) {
    ElMessage.error('没有解析到有效课程，请检查表头和内容')
    return
  }

  if (store.courses.length) {
    try {
      await ElMessageBox.confirm(
        `将用文件里的 ${courses.length} 门课替换当前课表，确定吗？`,
        '导入课表',
        { type: 'warning', confirmButtonText: '替换', cancelButtonText: '取消' },
      )
    } catch {
      return
    }
  }

  try {
    await store.replaceAll(courses)
    ElMessage.success(
      skipped ? `已导入 ${courses.length} 门课，跳过 ${skipped} 行` : `已导入 ${courses.length} 门课`,
    )
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '课表保存失败'))
  }
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">我的课表</h1>
        <p class="page-sub">2026-2027 学年第一学期 · 共 {{ store.courses.length }} 门课</p>
      </div>
      <div class="head-actions">
        <input
          ref="fileInput"
          type="file"
          accept=".csv,.xlsx,.xls"
          class="file-input"
          @change="onFileChange"
        />
        <el-tooltip
          content="支持 CSV / Excel，表头需包含：课程名称、星期、节次，教室和教师选填"
          placement="bottom"
        >
          <el-button :icon="Upload" @click="fileInput?.click()">导入课表</el-button>
        </el-tooltip>
        <el-button type="primary" :icon="Plus" @click="openCreate()">新增课程</el-button>
      </div>
    </div>

    <div v-loading="store.loading" class="board glass rise">
      <div class="row head">
        <div class="cell time">节次</div>
        <div
          v-for="(day, index) in weekdays"
          :key="day"
          class="cell day"
          :class="{ today: index === today }"
        >
          {{ day }}
          <span v-if="index === today">今天</span>
        </div>
      </div>

      <div v-for="(row, sectionIndex) in grid" :key="sectionIndex" class="row">
        <div class="cell time">{{ sections[sectionIndex] }}</div>
        <div
          v-for="(course, dayIndex) in row"
          :key="dayIndex"
          class="cell slot"
          :class="{ empty: !course }"
          @click="
            course ? openEdit(course) : openCreate(dayIndex + 1, sectionIndex + 1)
          "
        >
          <div v-if="course" class="course" :style="{ backgroundImage: course.color }">
            <strong>{{ course.name }}</strong>
            <span>{{ course.room }}</span>
            <small>{{ course.teacher }}</small>
          </div>
          <el-icon v-else class="slot-add" :size="18"><Plus /></el-icon>
        </div>
      </div>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId === null ? '新增课程' : '编辑课程'"
      width="460px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="课程名称" prop="name">
          <el-input v-model="form.name" placeholder="如：数据结构" />
        </el-form-item>
        <el-form-item label="星期" prop="day">
          <el-select v-model="form.day" placeholder="选择星期">
            <el-option
              v-for="(day, index) in weekdays"
              :key="day"
              :label="day"
              :value="index + 1"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="节次" prop="section">
          <el-select v-model="form.section" placeholder="选择节次">
            <el-option
              v-for="(section, index) in sections"
              :key="section"
              :label="section"
              :value="index + 1"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="教室">
          <el-input v-model="form.room" placeholder="如：信工楼 A301" />
        </el-form-item>
        <el-form-item label="教师">
          <el-input v-model="form.teacher" placeholder="如：王强" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button
          v-if="editingId !== null"
          type="danger"
          :icon="Delete"
          @click="removeCourse"
        >
          删除
        </el-button>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.head-actions {
  display: flex;
  gap: 10px;
}

.file-input {
  display: none;
}

.board {
  flex: 1;
  padding: 10px;
  overflow: auto;
}

.row {
  display: grid;
  grid-template-columns: 92px repeat(5, minmax(140px, 1fr));
  gap: 8px;
  margin-bottom: 8px;
}

.row.head {
  position: sticky;
  top: 0;
  z-index: 2;
}

.cell {
  padding: 10px;
}

.head .cell {
  padding: 12px 10px;
  font-size: 13px;
  font-weight: 600;
  text-align: center;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.04);
  border-radius: 12px;
}

.head .cell.today {
  color: #fff;
  background: rgba(139, 92, 246, 0.28);
}

.head .cell.today span {
  margin-left: 6px;
  font-size: 11px;
  color: #c4b5fd;
}

.cell.time {
  display: grid;
  place-items: center;
  font-size: 12px;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
}

.cell.slot {
  display: grid;
  place-items: center;
  min-height: 84px;
  padding: 4px;
  cursor: pointer;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.02);
}

.cell.slot.empty:hover {
  background: rgba(139, 92, 246, 0.1);
}

.slot-add {
  color: var(--text-muted);
  opacity: 0;
  transition: opacity 0.2s ease;
}

.cell.slot.empty:hover .slot-add {
  opacity: 0.7;
}

.course {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 3px;
  width: 100%;
  height: 100%;
  padding: 12px;
  color: #fff;
  border-radius: 10px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.course:hover {
  transform: translateY(-3px) scale(1.02);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.45);
}

.course strong {
  font-size: 13px;
}

.course span {
  font-size: 11px;
  opacity: 0.9;
}

.course small {
  font-size: 11px;
  opacity: 0.75;
}
</style>
