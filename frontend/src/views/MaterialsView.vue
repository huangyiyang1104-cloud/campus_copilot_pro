<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { ElMessage, ElMessageBox, type UploadFile } from 'element-plus'
import { Delete, Document, Download, UploadFilled } from '@element-plus/icons-vue'

import { getErrorMessage } from '@/api/http'
import {
  deleteMaterial,
  fetchDownloadUrl,
  fetchMaterials,
  uploadMaterial,
  type MaterialItem,
} from '@/api/materials'

const materials = ref<MaterialItem[]>([])
const loading = ref(false)
const uploading = ref(false)
const uploadPercent = ref(0)

let pollTimer: number | undefined

const statusText: Record<MaterialItem['status'], string> = {
  0: '排队中',
  1: '索引中',
  2: '已索引',
  3: '失败',
}

const statusType: Record<MaterialItem['status'], 'info' | 'warning' | 'success' | 'danger'> = {
  0: 'info',
  1: 'warning',
  2: 'success',
  3: 'danger',
}

function hasPending() {
  return materials.value.some((item) => item.status === 0 || item.status === 1)
}

function syncPolling() {
  if (hasPending() && pollTimer === undefined) {
    pollTimer = window.setInterval(() => {
      void load(false)
    }, 3000)
  } else if (!hasPending() && pollTimer !== undefined) {
    window.clearInterval(pollTimer)
    pollTimer = undefined
  }
}

async function load(showLoading = true) {
  if (showLoading) loading.value = true
  try {
    materials.value = await fetchMaterials()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '资料加载失败'))
  } finally {
    if (showLoading) loading.value = false
  }
  syncPolling()
}

onMounted(async () => {
  await load()
})

onUnmounted(() => {
  if (pollTimer !== undefined) window.clearInterval(pollTimer)
})

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function formatTime(value: string) {
  return value.replace('T', ' ').slice(0, 16)
}

async function onFileChange(file: UploadFile) {
  const raw = file.raw
  if (!raw) return

  if (raw.size > 20 * 1024 * 1024) {
    ElMessage.error('单个文件不能超过 20 MB')
    return
  }

  uploading.value = true
  uploadPercent.value = 0
  try {
    const material = await uploadMaterial(raw, undefined, (percent) => {
      uploadPercent.value = percent
    })
    materials.value.unshift(material)
    ElMessage.success('已上传，正在后台解析')
    syncPolling()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '上传失败'))
  } finally {
    uploading.value = false
  }
}

async function download(item: MaterialItem) {
  try {
    const { url } = await fetchDownloadUrl(item.id)
    const link = document.createElement('a')
    link.href = url
    link.target = '_blank'
    link.rel = 'noopener'
    link.click()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '获取下载地址失败'))
  }
}

async function remove(item: MaterialItem) {
  try {
    await ElMessageBox.confirm(`确定删除「${item.name}」吗？删除后 AI 将不再引用它。`, '删除资料', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }

  try {
    await deleteMaterial(item.id)
    materials.value = materials.value.filter((row) => row.id !== item.id)
    ElMessage.success('资料已删除')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '删除失败'))
  }
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">课程资料</h1>
        <p class="page-sub">上传课件后，助手会切片并写入向量库，回答时只检索你自己的资料</p>
      </div>
      <el-tag effect="plain" round>{{ materials.length }} 份资料</el-tag>
    </div>

    <div class="content">
      <el-upload
        class="uploader"
        drag
        :auto-upload="false"
        :show-file-list="false"
        :disabled="uploading"
        accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.md"
        :on-change="onFileChange"
      >
        <div class="drop">
          <el-icon :size="34" class="drop-icon"><UploadFilled /></el-icon>
          <strong>{{ uploading ? '正在上传…' : '把课件拖到这里，或点击选择文件' }}</strong>
          <span>支持 PDF / Word / PPT / Excel / Markdown，单个文件不超过 20 MB；PDF 超过 200 页会自动拆分</span>
        </div>
      </el-upload>

      <el-progress
        v-if="uploading"
        :percentage="uploadPercent"
        :stroke-width="6"
        class="upload-progress"
      />

      <div v-loading="loading" class="list glass rise">
        <div v-if="!loading && materials.length === 0" class="empty">
          还没有上传资料，传一份课件试试
        </div>

        <div v-for="item in materials" :key="item.id" class="item">
          <div class="file-icon">
            <el-icon :size="18"><Document /></el-icon>
          </div>

          <div class="file-info">
            <strong>{{ item.name }}</strong>
            <span>
              {{ item.course ?? '未归类' }} · {{ formatSize(item.size) }} ·
              {{ formatTime(item.created_at) }}
              <template v-if="item.status === 2"> · {{ item.chunk_count }} 个切片</template>
            </span>
            <small v-if="item.status === 3" class="error-text">{{ item.error_msg }}</small>
          </div>

          <el-tooltip
            :content="item.error_msg || statusText[item.status]"
            placement="top"
            :disabled="item.status !== 3"
          >
            <el-tag :type="statusType[item.status]" effect="plain" round size="small">
              {{ statusText[item.status] }}
            </el-tag>
          </el-tooltip>

          <div class="actions">
            <el-button
              text
              circle
              :icon="Download"
              title="下载 / 预览"
              @click="download(item)"
            />
            <el-button
              text
              circle
              type="danger"
              :icon="Delete"
              title="删除资料"
              @click="remove(item)"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
  overflow: auto;
}

.uploader {
  width: 100%;
}

.uploader :deep(.el-upload) {
  width: 100%;
}

.uploader :deep(.el-upload-dragger) {
  padding: 0;
  background: rgba(255, 255, 255, 0.04);
  border: 1px dashed rgba(167, 139, 250, 0.45);
  border-radius: var(--radius-lg);
  transition: all 0.22s ease;
}

.uploader :deep(.el-upload-dragger:hover) {
  background: rgba(139, 92, 246, 0.12);
  border-color: rgba(167, 139, 250, 0.85);
}

.drop {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 34px 20px;
}

.drop-icon {
  color: #a78bfa;
}

.drop strong {
  font-size: 14px;
}

.drop span {
  font-size: 12px;
  color: var(--text-muted);
}

.upload-progress {
  margin-top: -6px;
}

.list {
  padding: 8px;
}

.empty {
  padding: 40px 20px;
  font-size: 13px;
  color: var(--text-muted);
  text-align: center;
}

.item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px;
  border-radius: 14px;
  transition: background 0.2s ease;
}

.item:hover {
  background: rgba(255, 255, 255, 0.04);
}

.file-icon {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  color: #c4b5fd;
  border-radius: 12px;
  background: rgba(139, 92, 246, 0.16);
  flex-shrink: 0;
}

.file-info {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.file-info strong {
  overflow: hidden;
  font-size: 13px;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.file-info span {
  font-size: 12px;
  color: var(--text-muted);
}

.error-text {
  overflow: hidden;
  font-size: 11px;
  color: #f87171;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.actions {
  display: flex;
  gap: 2px;
}
</style>
