<template>
  <component
    :is="pageComponent"
    v-bind="aiChatEnabled ? {} : placeholderProps"
  />
</template>

<script setup lang="ts">
import { defineAsyncComponent } from 'vue'

const aiChatEnabled =
  import.meta.env.VITE_ENABLE_AI_CHAT === 'true'

const pageComponent = aiChatEnabled
  ? defineAsyncComponent(
      () => import('./EmotionalChatView.vue'),
    )
  : defineAsyncComponent(
      () => import('./ComingSoonView.vue'),
    )

const placeholderProps = {
  title: '情感陪伴',
  eyebrow: 'AI 对话',
  description:
    '聊天功能将在社交空间完成验收后启用，提供流式回复、会话历史和危机求助提示。',
  items: [
    '多轮情绪对话',
    '会话历史与隐私隔离',
    '安全提示与紧急求助入口',
  ],
}
</script>
