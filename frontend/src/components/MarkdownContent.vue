<script lang="ts">
import DOMPurify from 'dompurify'

// 模块级只注册一次，避免每个消息组件实例都挂一个 hook
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank')
    node.setAttribute('rel', 'noopener noreferrer')
  }
})
</script>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps<{ content: string }>()

const html = computed(() => {
  const raw = marked.parse(props.content, {
    async: false,
    gfm: true,
    breaks: true,
  }) as string

  return DOMPurify.sanitize(raw, { USE_PROFILES: { html: true } })
})
</script>

<template>
  <div class="markdown-body" v-html="html" />
</template>

<style scoped>
.markdown-body {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-main);
  word-break: break-word;
}

.markdown-body :deep(> :first-child) {
  margin-top: 0;
}

.markdown-body :deep(> :last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(p) {
  margin: 0 0 10px;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 16px 0 8px;
  font-weight: 700;
  line-height: 1.45;
}

.markdown-body :deep(h1) {
  font-size: 19px;
}

.markdown-body :deep(h2) {
  font-size: 17px;
}

.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  font-size: 15px;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 6px 0 10px;
  padding-left: 22px;
}

.markdown-body :deep(li) {
  margin: 4px 0;
}

.markdown-body :deep(li > p) {
  margin: 0;
}

.markdown-body :deep(strong) {
  font-weight: 700;
  color: #f5f3ff;
}

.markdown-body :deep(em) {
  color: #ddd6fe;
}

.markdown-body :deep(code) {
  padding: 1px 5px;
  font-family: ui-monospace, SFMono-Regular, Consolas, 'Liberation Mono', monospace;
  font-size: 0.9em;
  background: rgba(0, 0, 0, 0.28);
  border-radius: 5px;
}

.markdown-body :deep(pre) {
  margin: 10px 0;
  padding: 10px 12px;
  overflow-x: auto;
  background: rgba(0, 0, 0, 0.28);
  border: 1px solid var(--stroke);
  border-radius: 10px;
}

.markdown-body :deep(pre code) {
  padding: 0;
  background: transparent;
  border-radius: 0;
}

.markdown-body :deep(blockquote) {
  margin: 10px 0;
  padding: 2px 0 2px 10px;
  color: var(--text-muted);
  border-left: 3px solid #8b5cf6;
}

.markdown-body :deep(a) {
  color: #a78bfa;
  text-decoration: underline;
  word-break: break-all;
}

.markdown-body :deep(hr) {
  margin: 14px 0;
  border: 0;
  border-top: 1px solid var(--stroke);
}

.markdown-body :deep(table) {
  display: block;
  width: 100%;
  margin: 10px 0;
  overflow-x: auto;
  border-collapse: collapse;
  font-size: 13px;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  padding: 6px 8px;
  border: 1px solid var(--stroke);
  text-align: left;
}

.markdown-body :deep(th) {
  background: rgba(255, 255, 255, 0.05);
}

.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: 8px;
}
</style>
