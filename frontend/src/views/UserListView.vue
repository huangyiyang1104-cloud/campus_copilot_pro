<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Delete, Edit, Plus } from '@element-plus/icons-vue'

import { getErrorMessage } from '@/api/http'
import type { UserItem } from '@/api/users'
import { useUserStore } from '@/stores/users'

const store = useUserStore()

const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const saving = ref(false)

const form = reactive({
  username: '',
  password: '',
  name: '',
  role: 'student' as UserItem['role'],
  email: '',
  phone: '',
  status: 1 as UserItem['status'],
})

const dialogTitle = computed(() => (editingId.value === null ? '新增用户' : '编辑用户'))

const rules = computed<FormRules>(() => ({
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  // 新增时密码必填；编辑时密码留空表示不修改
  password:
    editingId.value === null
      ? [
          { required: true, message: '请输入密码', trigger: 'blur' },
          { min: 6, message: '密码至少 6 位', trigger: 'blur' },
        ]
      : [{ min: 6, message: '密码至少 6 位', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}))

function formatTime(value: string) {
  return value.replace('T', ' ').slice(0, 19)
}

onMounted(async () => {
  try {
    await store.load()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '用户列表加载失败'))
  }
})

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    username: '',
    password: '',
    name: '',
    role: 'student',
    email: '',
    phone: '',
    status: 1,
  })
  dialogVisible.value = true
}

function openEdit(row: UserItem) {
  editingId.value = row.id
  Object.assign(form, {
    username: row.username,
    password: '',
    name: row.name,
    role: row.role,
    email: row.email ?? '',
    phone: row.phone ?? '',
    status: row.status,
  })
  dialogVisible.value = true
}

async function submit() {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (editingId.value === null) {
      await store.create({
        username: form.username,
        password: form.password,
        name: form.name,
        role: form.role,
        email: form.email,
        phone: form.phone,
        avatar: '',
        status: form.status,
      })
      ElMessage.success('用户已创建')
    } else {
      await store.update(editingId.value, {
        username: form.username,
        password: form.password || undefined,
        name: form.name,
        role: form.role,
        email: form.email,
        phone: form.phone,
        status: form.status,
      })
      ElMessage.success('用户已更新')
    }

    dialogVisible.value = false
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function remove(row: UserItem) {
  try {
    await ElMessageBox.confirm(`确定删除用户「${row.name}」吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }

  try {
    await store.remove(row.id)
    ElMessage.success('已删除')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '删除失败'))
  }
}

async function toggleStatus(row: UserItem) {
  // 开关的 v-model 已经把 row.status 改成了新值，直接用
  const next = row.status

  try {
    await store.changeStatus(row.id, next)
    ElMessage.success(next === 1 ? `已启用「${row.name}」` : `已禁用「${row.name}」`)
  } catch (error) {
    // 接口失败时把开关拨回去
    row.status = next === 1 ? 0 : 1
    ElMessage.error(getErrorMessage(error, '状态修改失败'))
  }
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-sub">仅管理员可见，可对账号进行新增、编辑、删除</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreate">新增用户</el-button>
    </div>

    <div v-loading="store.loading" class="table-wrap glass rise">
      <el-table :data="store.users" height="100%" style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="账号" min-width="120" />
        <el-table-column prop="name" label="姓名" min-width="110" />
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" effect="plain" round>
              {{ row.role === 'admin' ? '管理员' : '学生' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
        <el-table-column prop="phone" label="手机号" min-width="130" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-switch
              v-model="row.status"
              :active-value="1"
              :inactive-value="0"
              @change="toggleStatus(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="170">
          <template #default="{ row }">{{ formatTime(row.create_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" :icon="Edit" @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" :icon="Delete" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="480px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="72px">
        <el-form-item label="账号" prop="username">
          <el-input v-model="form.username" placeholder="登录账号" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="editingId === null ? '登录密码' : '留空表示不修改'"
          />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" placeholder="真实姓名" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-radio-group v-model="form.role">
            <el-radio value="student">学生</el-radio>
            <el-radio value="admin">管理员</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="选填" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" placeholder="选填" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" />
          <span class="status-tip">{{ form.status === 1 ? '正常' : '禁用' }}</span>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.table-wrap {
  flex: 1;
  min-height: 0;
  padding: 10px 14px;
  overflow: hidden;
}

.table-wrap :deep(.el-table) {
  background: transparent;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-border-color: rgba(255, 255, 255, 0.06);
}

.table-wrap :deep(.el-table th) {
  font-weight: 600;
  color: var(--text-muted);
}

.status-tip {
  margin-left: 10px;
  font-size: 12px;
  color: var(--text-muted);
}
</style>
