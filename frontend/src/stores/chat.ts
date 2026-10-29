import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import {
  createConversation as createConversationApi,
  deleteConversation as deleteConversationApi,
  fetchConversationMessages,
  fetchConversations,
  streamChat,
  type ChatMessageItem,
} from '@/api/chat'

export interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  time: string
}

export interface Conversation {
  id: number
  title: string
  messages: Message[]
  /** 最后一条消息的时间戳，列表按它倒序 */
  updatedAt: number
}

const ACTIVE_KEY = 'activeConversationId'

function pad(value: number) {
  return String(value).padStart(2, '0')
}

function clockOf(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function timestampOf(value: string) {
  const timestamp = Date.parse(value)
  return Number.isNaN(timestamp) ? Date.now() : timestamp
}

function toMessage(item: ChatMessageItem): Message {
  return {
    id: item.id,
    role: item.role,
    content: item.content,
    time: clockOf(item.created_at),
  }
}

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<Conversation[]>([])
  const activeId = ref<number | null>(null)
  const sending = ref(false)
  const loading = ref(false)
  const creating = ref(false)

  let messageSeed = 0
  let creatingTask: Promise<Conversation> | null = null

  const activeConversation = computed(
    () => conversations.value.find((item) => item.id === activeId.value) ?? null,
  )
  const messages = computed(() => activeConversation.value?.messages ?? [])
  const sortedConversations = computed(() =>
    [...conversations.value].sort((a, b) => b.updatedAt - a.updatedAt),
  )

  function rememberActive(id: number | null) {
    if (id === null) localStorage.removeItem(ACTIVE_KEY)
    else localStorage.setItem(ACTIVE_KEY, String(id))
  }

  async function loadMessages(conversationId: number) {
    const rows = await fetchConversationMessages(conversationId)
    const conversation = conversations.value.find((item) => item.id === conversationId)
    if (!conversation) return
    conversation.messages = rows.map(toMessage)
  }

  /** 页面加载时从 MySQL 拉会话列表，并恢复上次选中的会话 */
  async function loadConversations() {
    loading.value = true
    try {
      const rows = await fetchConversations()
      conversations.value = rows.map((item) => ({
        id: item.id,
        title: item.title,
        messages: [],
        updatedAt: timestampOf(item.updated_at),
      }))

      const saved = Number(localStorage.getItem(ACTIVE_KEY))
      const target =
        conversations.value.find((item) => item.id === saved) ?? conversations.value[0] ?? null

      activeId.value = target?.id ?? null
      rememberActive(activeId.value)

      if (target) await loadMessages(target.id)
    } finally {
      loading.value = false
    }
  }

  async function createConversation() {
    // 新建按钮和“没有会话时直接发送”可能同时触发，复用同一个请求
    if (creatingTask) return creatingTask

    creating.value = true
    const task = (async () => {
      const item = await createConversationApi()
      const conversation: Conversation = {
        id: item.id,
        title: item.title,
        messages: [],
        updatedAt: timestampOf(item.updated_at),
      }

      conversations.value.unshift(conversation)
      activeId.value = conversation.id
      rememberActive(conversation.id)
      return conversation
    })()

    creatingTask = task
    try {
      return await task
    } finally {
      creating.value = false
      creatingTask = null
    }
  }

  async function selectConversation(id: number) {
    if (sending.value) return

    activeId.value = id
    rememberActive(id)
    await loadMessages(id)
  }

  async function removeConversation(id: number) {
    if (sending.value) return

    await deleteConversationApi(id)
    conversations.value = conversations.value.filter((item) => item.id !== id)

    if (activeId.value === id) {
      const next = conversations.value[0] ?? null
      activeId.value = next?.id ?? null
      rememberActive(activeId.value)
      if (next) await loadMessages(next.id)
    }
  }

  async function send(text: string) {
    const question = text.trim()
    if (!question || sending.value) return

    let conversation = activeConversation.value
    if (!conversation) conversation = await createConversation()

    const target = conversation
    const firstMessage = target.messages.length === 0

    target.messages.push({
      id: --messageSeed,
      role: 'user',
      content: question,
      time: clockOf(new Date().toISOString()),
    })
    if (firstMessage) target.title = question.slice(0, 20)

    const reply: Message = {
      id: --messageSeed,
      role: 'assistant',
      content: '',
      time: clockOf(new Date().toISOString()),
    }
    target.messages.push(reply)
    target.updatedAt = Date.now()
    sending.value = true

    try {
      const done = await streamChat(
        { conversation_id: target.id, message: question },
        (delta) => {
          reply.content += delta
        },
      )
      if (done?.title) target.title = done.title
    } catch (error) {
      // 一个字都没收到就把空气泡去掉
      if (!reply.content) {
        target.messages = target.messages.filter((item) => item.id !== reply.id)
      }
      throw error
    } finally {
      sending.value = false
      target.updatedAt = Date.now()
    }

    // 流式过程中用的是临时 id，结束后用数据库里的最终消息替换
    try {
      await loadMessages(target.id)
    } catch {
      // 刷新失败不影响刚才已经看到的内容，下次切换会话会重新拉
    }
  }

  return {
    conversations,
    activeId,
    activeConversation,
    messages,
    sortedConversations,
    sending,
    loading,
    creating,
    loadConversations,
    createConversation,
    selectConversation,
    removeConversation,
    send,
  }
})
