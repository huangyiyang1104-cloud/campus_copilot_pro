import { ref } from 'vue'
import { defineStore } from 'pinia'

import { synthesizeSpeech } from '@/api/tts'

/** 语气标签与后端 tts.py 的 TAG_STYLES 保持一致 */
const TAGS = new Set([
  '小声',
  '紧张地',
  '鼓起勇气',
  '认真地',
  '难过',
  '开心',
  '害羞',
  '平静',
])

const ALIASES: Record<string, string> = {
  紧张: '紧张地',
  害怕: '紧张地',
  认真: '认真地',
  小声地: '小声',
  紧张地说: '紧张地',
  害怕地: '紧张地',
  认真地说: '认真地',
  平静地: '平静',
  开心地: '开心',
  难过地: '难过',
  害羞地: '害羞',
  鼓起勇气说: '鼓起勇气',
}

type SegmentStatus = 'pending' | 'loading' | 'ready' | 'played' | 'error'

interface Segment {
  id: number
  text: string
  tag: string
  status: SegmentStatus
  url?: string
}

const TAG_RE = /^\s*[\[【]([^\]】]+)[\]】]\s*/
const ANY_TAG_RE = /[\[【]([^\]】]+)[\]】]/
const TAG_WORDS = [...TAGS, ...Object.keys(ALIASES)].join('|')
const TAG_TAIL_RE = new RegExp(`(?:[\\[【])?(?:${TAG_WORDS})[\\]】]`, 'g')
const COMPLETE_SENTENCE_RE = /[^。！？!?…\n]+(?:[。！？!?…]+|\n)/g

function normalizeTag(raw: string): string {
  const value = (ALIASES[raw] ?? raw).trim()
  return TAGS.has(value) ? value : '平静'
}

function cleanSpeechText(text: string): string {
  return text
    .replace(ANY_TAG_RE, '')
    .replace(TAG_TAIL_RE, '')
    .replace(/^[\[\]【】\s]+/, '')
    .replace(/\s+/g, ' ')
    .trim()
}

export const useSpeechStore = defineStore('speech', () => {
  const enabled = ref(true)
  const speaking = ref(false)
  const activeText = ref('')
  const activeTag = ref('')
  const blocked = ref(false)

  let buffer = ''
  let currentTag = '平静'
  let segments: Segment[] = []
  let playIndex = 0
  let audio: HTMLAudioElement | null = null
  let pendingCount = 0
  let nextId = 0
  let generation = 0

  function enqueue(raw: string) {
    const text = cleanSpeechText(raw)
    if (!text || !/[\u4e00-\u9fffA-Za-z0-9]/.test(text)) return

    segments.push({
      id: nextId++,
      text,
      tag: currentTag,
      status: 'pending',
    })
    pump()
  }

  function emitText(text: string, final: boolean) {
    if (!text) return

    if (final) {
      enqueue(text)
      return
    }

    let lastIndex = 0
    let match: RegExpExecArray | null
    COMPLETE_SENTENCE_RE.lastIndex = 0

    while ((match = COMPLETE_SENTENCE_RE.exec(text)) !== null) {
      enqueue(match[0])
      lastIndex = COMPLETE_SENTENCE_RE.lastIndex
    }

    buffer = text.slice(lastIndex)
  }

  /** 从流式文本里拆出完整句子；final=true 时把剩余文本也吐出来 */
  function drain(final: boolean) {
    while (buffer.length > 0) {
      const tagMatch = buffer.match(TAG_RE)
      if (tagMatch && tagMatch.index === 0) {
        currentTag = normalizeTag(tagMatch[1])
        buffer = buffer.slice(tagMatch[0].length)
        continue
      }

      const anyTag = buffer.match(ANY_TAG_RE)
      if (anyTag && anyTag.index !== undefined && anyTag.index > 0) {
        const head = buffer.slice(0, anyTag.index)
        buffer = buffer.slice(anyTag.index)
        emitText(head, true)
        continue
      }

      // 标签还没收全，先留着，避免把 "[紧" 当正文合成
      if (!final) {
        const openBracket = buffer.lastIndexOf('[')
        const openFullwidth = buffer.lastIndexOf('【')
        const open = Math.max(openBracket, openFullwidth)
        if (open >= 0 && !/[\[【][^\]】]*[\]】]/.test(buffer.slice(open))) {
          const head = buffer.slice(0, open)
          buffer = buffer.slice(open)
          emitText(head, false)
          return
        }
      }

      emitText(buffer, final)
      if (final) buffer = ''
      return
    }
  }

  function pump() {
    while (pendingCount < 2) {
      const segment = segments.find((item) => item.status === 'pending')
      if (!segment) break

      segment.status = 'loading'
      pendingCount += 1
      const requestGeneration = generation

      synthesizeSpeech(segment.text, segment.tag)
        .then((blob) => {
          if (requestGeneration !== generation || !segments.includes(segment)) return
          segment.url = URL.createObjectURL(blob)
          segment.status = 'ready'
          tryPlay()
        })
        .catch(() => {
          if (requestGeneration !== generation || !segments.includes(segment)) return
          segment.status = 'error'
          tryPlay()
        })
        .finally(() => {
          pendingCount -= 1
          if (requestGeneration === generation) pump()
        })
    }
  }

  function tryPlay() {
    if (!enabled.value || speaking.value || blocked.value) return

    while (playIndex < segments.length) {
      const segment = segments[playIndex]

      if (segment.status === 'error') {
        playIndex += 1
        continue
      }
      if (segment.status !== 'ready' || !segment.url) return

      audio = new Audio(segment.url)
      audio.onended = () => {
        URL.revokeObjectURL(segment.url!)
        segment.status = 'played'
        audio = null
        speaking.value = false
        activeText.value = ''
        activeTag.value = ''
        playIndex += 1
        tryPlay()
      }
      audio.onerror = () => {
        segment.status = 'error'
        audio = null
        speaking.value = false
        activeText.value = ''
        activeTag.value = ''
        playIndex += 1
        tryPlay()
      }

      speaking.value = true
      activeText.value = segment.text
      activeTag.value = segment.tag
      audio.play().catch(() => {
        speaking.value = false
        blocked.value = true
      })
      return
    }
  }

  function begin() {
    if (!enabled.value) return
    stop()
    buffer = ''
    currentTag = '平静'
    segments = []
    playIndex = 0
    generation += 1
  }

  function feed(delta: string) {
    if (!enabled.value) return
    buffer += delta
    drain(false)
  }

  function end() {
    if (!enabled.value) {
      buffer = ''
      return
    }
    drain(true)
    pump()
  }

  async function resume() {
    blocked.value = false
    if (audio) {
      try {
        await audio.play()
        speaking.value = true
      } catch {
        blocked.value = true
      }
      return
    }
    tryPlay()
  }

  function stop() {
    generation += 1
    audio?.pause()
    audio = null
    segments.forEach((segment) => {
      if (segment.url) URL.revokeObjectURL(segment.url)
    })
    segments = []
    playIndex = 0
    buffer = ''
    activeText.value = ''
    activeTag.value = ''
    speaking.value = false
    blocked.value = false
  }

  function toggle() {
    enabled.value = !enabled.value
    if (!enabled.value) stop()
  }

  return {
    enabled,
    speaking,
    activeText,
    activeTag,
    blocked,
    begin,
    feed,
    end,
    stop,
    resume,
    toggle,
  }
})
