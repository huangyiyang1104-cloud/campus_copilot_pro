import http from '@/api/http'
import { clearSession, getToken, setToken } from '@/api/token'

export interface ChatPayload {
  conversation_id: number
  message: string
}

export interface ConversationItem {
  id: number
  title: string
  created_at: string
  updated_at: string
}

export interface ChatMessageItem {
  id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

interface StreamEvent {
  type: 'delta' | 'done' | 'error'
  content?: string
  message?: string
  conversation_id?: number
  title?: string
}

export interface ChatDoneInfo {
  conversation_id: number
  title?: string
}

export function fetchConversations() {
  return http.get<ConversationItem[]>('/conversations').then((response) => response.data)
}

export function createConversation() {
  return http.post<ConversationItem>('/conversations').then((response) => response.data)
}

export function fetchConversationMessages(conversationId: number) {
  return http
    .get<ChatMessageItem[]>(`/conversations/${conversationId}/messages`)
    .then((response) => response.data)
}

export function deleteConversation(conversationId: number) {
  return http
    .delete<{ message: string }>(`/conversations/${conversationId}`)
    .then((response) => response.data)
}

async function refreshAccessToken() {
  const { data } = await http.post<{ access_token: string }>('/auth/refresh')
  setToken(data.access_token)
}

async function readErrorMessage(response: Response) {
  try {
    const data = await response.json()
    const detail = data?.detail
    if (typeof detail === 'string') return detail
    if (detail && typeof detail === 'object' && 'message' in detail) {
      return String(detail.message)
    }
  } catch {
    // 响应不是 JSON，用状态码兜底
  }
  return `对话请求失败（${response.status}）`
}

function parseEvent(line: string): StreamEvent | null {
  if (!line.startsWith('data:')) return null
  const payload = line.slice(5).trim()
  if (!payload) return null

  try {
    return JSON.parse(payload) as StreamEvent
  } catch {
    return null
  }
}

/** 调用流式对话接口，每收到一段增量就回调一次 onDelta */
export async function streamChat(
  payload: ChatPayload,
  onDelta: (text: string) => void,
): Promise<ChatDoneInfo | null> {
  const request = () =>
    fetch('/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify(payload),
    })

  let response = await request()

  // fetch 走不到 axios 拦截器，AT 过期时在这里换一次
  if (response.status === 401) {
    try {
      await refreshAccessToken()
    } catch {
      clearSession()
      window.location.assign('/login')
      throw new Error('登录已失效，请重新登录')
    }
    response = await request()
  }

  if (!response.ok || !response.body) {
    throw new Error(await readErrorMessage(response))
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finished = false
  let doneInfo: ChatDoneInfo | null = null

  while (!finished) {
    const { value, done } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      const event = parseEvent(line)
      if (!event) continue

      if (event.type === 'delta' && event.content) {
        onDelta(event.content)
      } else if (event.type === 'error') {
        await reader.cancel()
        throw new Error(event.message ?? 'AI 服务暂时不可用，请稍后重试')
      } else if (event.type === 'done') {
        doneInfo = {
          conversation_id: event.conversation_id ?? payload.conversation_id,
          title: event.title,
        }
        finished = true
        await reader.cancel()
        break
      }
    }
  }

  return doneInfo
}
