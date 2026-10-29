<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Expand, Fold, MagicStick, Plus, Promotion } from '@element-plus/icons-vue'

import { getErrorMessage } from '@/api/http'
import MarkdownContent from '@/components/MarkdownContent.vue'
import { suggestions } from '@/mock/chat'
import { useAuthStore } from '@/stores/auth'
import { useChatStore, type Conversation } from '@/stores/chat'

const chat = useChatStore()
const auth = useAuthStore()

const input = ref('')
const listRef = ref<HTMLElement | null>(null)
const historyCollapsed = ref(false)

const isEmpty = computed(() => chat.messages.length === 0)

function formatTime(timestamp: number) {
  const date = new Date(timestamp)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

async function scrollToBottom() {
  await nextTick()
  const el = listRef.value
  if (el) el.scrollTop = el.scrollHeight
}

async function send(text?: string) {
  const content = (text ?? input.value).trim()
  if (!content || chat.sending) return
  input.value = ''

  try {
    await chat.send(content)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'AI 回复失败，请稍后重试')
  }
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    send()
  }
}

async function removeConversation(conversation: Conversation) {
  try {
    await ElMessageBox.confirm(`确定删除会话「${conversation.title}」吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }

  try {
    await chat.removeConversation(conversation.id)
    ElMessage.success('已删除')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '删除会话失败'))
  }
}

async function newConversation() {
  try {
    await chat.createConversation()
    await scrollToBottom()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '新建会话失败'))
  }
}

async function openConversation(id: number) {
  if (chat.sending) return
  try {
    await chat.selectConversation(id)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '会话加载失败'))
  }
}

// 从其他路由切回来时组件会重新挂载：拉历史会话，再把消息滚到最新一条
onMounted(async () => {
  try {
    await chat.loadConversations()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '会话列表加载失败'))
  }
  await scrollToBottom()
})

// 切换会话（哪怕两边内容一样长）也要跳到底部
watch(() => chat.activeId, scrollToBottom)

// 内容每变化一次就跟着滚到底部（含流式输出）
watch(
  () => chat.messages.map((item) => item.content).join('').length,
  scrollToBottom,
)
</script>

<template>
  <div class="chat-page">

    <div class="chat-main">
      <header class="chat-head glass">
        <div class="head-left">
          <div class="bot-avatar">
            <el-icon :size="20"><MagicStick /></el-icon>
          </div>
          <div>
            <strong>{{ chat.activeConversation?.title ?? 'Campus Copilot' }}</strong>
            <p>课程助手 · 已连接校园数据</p>
          </div>
        </div>
        <div class="head-right">
          <span class="online"><i />在线</span>
          <el-button
            text
            circle
            :icon="historyCollapsed ? Expand : Fold"
            :title="historyCollapsed ? '展开会话列表' : '收起会话列表'"
            @click="historyCollapsed = !historyCollapsed"
          />
        </div>
      </header>

      <section ref="listRef" class="chat-list">
        <div v-if="isEmpty" class="empty rise">
          <div class="empty-avatar">
            <el-icon :size="30"><MagicStick /></el-icon>
          </div>
          <h2>
            你好，{{ auth.user?.name ?? '同学' }}，今天想查点什么？
          </h2>
          <p>我能查课表、按课件回答问题、帮你排学习计划。</p>
          <div class="chips">
            <button v-for="item in suggestions" :key="item" class="chip" @click="send(item)">
              {{ item }}
            </button>
          </div>
        </div>

        <div
          v-for="message in chat.messages"
          :key="message.id"
          class="message"
          :class="message.role === 'user' ? 'is-user' : 'is-bot'"
        >
          <div v-if="message.role === 'assistant'" class="avatar bot">
            <el-icon :size="16"><MagicStick /></el-icon>
          </div>

          <div class="bubble">
            <template v-if="message.content">
              <MarkdownContent
                v-if="message.role === 'assistant'"
                :content="message.content"
              />
              <p v-else>{{ message.content }}</p>
            </template>
            <span v-else class="typing"><i /><i /><i /></span>
            <time>{{ message.time }}</time>
          </div>

          <el-avatar v-if="message.role === 'user'" :size="32" class="avatar user">
            {{ auth.user?.name?.[0] ?? '我' }}
          </el-avatar>
        </div>
      </section>

      <footer class="chat-input glass">
        <el-input
          v-model="input"
          type="textarea"
          :autosize="{ minRows: 1, maxRows: 4 }"
          resize="none"
          placeholder="问我课表、课件内容，或者让我排一份复习计划…（Enter 发送，Shift + Enter 换行）"
          @keydown="onKeydown"
        />
        <el-button type="primary" :icon="Promotion" :disabled="chat.sending" @click="send()">
          发送
        </el-button>
      </footer>
    </div>

    <aside class="history glass" :class="{ collapsed: historyCollapsed }">
      <div class="history-inner">
        <el-button
          type="primary"
          :icon="Plus"
          class="new-btn"
          :disabled="chat.creating"
          @click="newConversation"
        >
          新建对话
        </el-button>

        <div class="history-list">
          <div
            v-for="item in chat.sortedConversations"
            :key="item.id"
            class="history-item"
            :class="{ active: item.id === chat.activeId }"
            @click="openConversation(item.id)"
          >
            <div class="history-text">
              <strong>{{ item.title }}</strong>
              <span>{{ formatTime(item.updatedAt) }}</span>
            </div>
            <el-button
              text
              circle
              size="small"
              :icon="Delete"
              :disabled="chat.sending"
              @click.stop="removeConversation(item)"
            />
          </div>

          <p v-if="chat.conversations.length === 0" class="history-empty">还没有对话</p>
        </div>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.chat-page {
  display: flex;
  height: 100%;
  min-height: 0;
}

.chat-main {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
  min-height: 0;
}

/* ---------- 历史会话 ---------- */
.history {
  width: 220px;
  margin-left: 14px;
  padding: 14px 10px;
  flex-shrink: 0;
  overflow: hidden;
  transition:
    width 0.3s cubic-bezier(0.4, 0, 0.2, 1),
    margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1),
    padding 0.3s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 0.2s ease;
}

.history.collapsed {
  width: 0;
  margin-left: 0;
  padding-right: 0;
  padding-left: 0;
  opacity: 0;
  border-width: 0;
}

.history-inner {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 200px;
  height: 100%;
}

.new-btn {
  width: 100%;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 10px;
  cursor: pointer;
  border-radius: 10px;
  transition: all 0.2s ease;
}

.history-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.history-item.active {
  background: rgba(139, 92, 246, 0.2);
}

.history-text {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  line-height: 1.35;
}

.history-text strong {
  overflow: hidden;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-main);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-text span {
  margin-top: 2px;
  font-size: 11px;
  color: var(--text-muted);
}

.history-empty {
  padding: 12px 8px;
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
}

/* ---------- 头部 ---------- */
.chat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
}

.head-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.bot-avatar {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  color: #fff;
  border-radius: 13px;
  background: var(--grad);
  box-shadow: 0 8px 20px rgba(124, 58, 237, 0.35);
  flex-shrink: 0;
}

.head-left strong {
  display: block;
  max-width: 420px;
  overflow: hidden;
  font-size: 15px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.head-left p {
  margin: 3px 0 0;
  font-size: 12px;
  color: var(--text-muted);
}

.head-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.online {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #34d399;
}

.online i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 0 4px rgba(52, 211, 153, 0.16);
}

.chat-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 8px 6px;
}

/* ---------- 空状态 ---------- */
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 20px;
  text-align: center;
}

.empty-avatar {
  display: grid;
  place-items: center;
  width: 68px;
  height: 68px;
  margin-bottom: 18px;
  color: #fff;
  border-radius: 22px;
  background: var(--grad);
  box-shadow: 0 16px 40px rgba(124, 58, 237, 0.35);
}

.empty h2 {
  margin: 0;
  font-size: 22px;
}

.empty p {
  margin: 10px 0 24px;
  font-size: 13px;
  color: var(--text-muted);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  max-width: 620px;
}

.chip {
  padding: 10px 16px;
  font-size: 13px;
  color: var(--text-main);
  cursor: pointer;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--stroke);
  border-radius: 999px;
  transition: all 0.2s ease;
}

.chip:hover {
  color: #fff;
  background: rgba(139, 92, 246, 0.22);
  border-color: rgba(167, 139, 250, 0.5);
  transform: translateY(-2px);
}

/* ---------- 消息 ---------- */
.message {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.message.is-user {
  justify-content: flex-end;
}

.avatar {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  color: #fff;
  border-radius: 10px;
}

.avatar.bot {
  background: var(--grad);
}

.avatar.user {
  background: linear-gradient(135deg, #0ea5e9, #6366f1);
  font-size: 13px;
  font-weight: 600;
}

.bubble {
  max-width: min(78%, 720px);
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--stroke);
  border-radius: 4px 16px 16px;
}

.is-user .bubble {
  color: #fff;
  background: var(--grad);
  border: none;
  border-radius: 16px 4px 16px 16px;
}

.bubble > p {
  margin: 0;
  font-size: 14px;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
}

.bubble time {
  display: block;
  margin-top: 8px;
  font-size: 11px;
  color: var(--text-muted);
  text-align: right;
}

.is-user .bubble time {
  color: rgba(255, 255, 255, 0.7);
}

.typing {
  display: inline-flex;
  gap: 5px;
  align-items: center;
  height: 20px;
}

.typing i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.5);
  animation: blink 1.2s infinite ease-in-out;
}

.typing i:nth-child(2) {
  animation-delay: 0.2s;
}

.typing i:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes blink {
  0%,
  100% {
    opacity: 0.25;
    transform: translateY(0);
  }
  50% {
    opacity: 1;
    transform: translateY(-3px);
  }
}

/* ---------- 输入区 ---------- */
.chat-input {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  padding: 12px 14px;
}

.chat-input :deep(.el-textarea__inner) {
  background: transparent;
  box-shadow: none;
  font-size: 14px;
}
</style>
