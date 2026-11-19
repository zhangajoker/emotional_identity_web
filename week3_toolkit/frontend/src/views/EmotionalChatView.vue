<template>
  <section class="chat-layout">
    <aside class="session-panel">
      <div class="session-heading">
        <div>
          <p class="eyebrow">对话记录</p>
          <h2>心情谈话</h2>
        </div>
        <button type="button" class="new-chat" @click="newConversation">
          新对话
        </button>
      </div>

      <div v-if="sessionsLoading" class="session-empty">正在读取...</div>
      <div v-else-if="sessions.length === 0" class="session-empty">
        还没有对话
      </div>
      <div v-else class="session-list">
        <button
          v-for="session in sessions"
          :key="session.id"
          type="button"
          :class="[
            'session-item',
            { active: session.id === activeSessionId },
          ]"
          @click="selectSession(session.id)"
        >
          <strong>{{ session.title }}</strong>
          <span>{{ session.last_message || '还没有消息' }}</span>
        </button>
      </div>
    </aside>

    <div class="chat-panel">
      <header class="chat-header">
        <div>
          <p class="eyebrow">心语 · AI 情感陪伴</p>
          <h2>{{ activeSession?.title || '新的对话' }}</h2>
        </div>
        <button
          v-if="activeSessionId"
          type="button"
          class="delete-chat"
          :disabled="streaming"
          @click="deleteConversation"
        >
          删除对话
        </button>
      </header>

      <div class="safety-banner">
        心语提供日常情感支持，不作医疗诊断或替代专业治疗。
        如果你或他人正面临立即危险，请拨打 120 或 110，并联系身边可信任的人。
      </div>

      <div ref="messageArea" class="message-area">
        <div v-if="messagesLoading" class="empty-chat">
          正在读取对话...
        </div>

        <div v-else-if="messages.length === 0" class="empty-chat">
          <div class="empty-symbol">◌</div>
          <h3>你好，我在这里听你说</h3>
          <p>可以从今天最让你在意的一件小事开始。</p>
          <div class="prompt-list">
            <button
              v-for="prompt in starterPrompts"
              :key="prompt"
              type="button"
              @click="draft = prompt"
            >
              {{ prompt }}
            </button>
          </div>
        </div>

        <template v-else>
          <article
            v-for="message in messages"
            :key="message.id"
            :class="[
              'message-row',
              message.role,
              { safety: message.safety_flag },
            ]"
          >
            <div class="message-author">
              {{ message.role === 'user' ? '你' : '心语' }}
            </div>
            <div class="message-bubble">
              <p>{{ message.content }}</p>
              <span v-if="message.safety_flag" class="safety-label">
                安全提醒
              </span>
            </div>
          </article>
        </template>
      </div>

      <form class="chat-composer" @submit.prevent="sendMessage">
        <el-input
          v-model="draft"
          type="textarea"
          :rows="3"
          maxlength="2000"
          resize="none"
          placeholder="写下此刻的感受，心语会认真听..."
          :disabled="!activeSessionId"
          @keydown.enter.exact.prevent="sendMessage"
        />

        <div class="composer-footer">
          <span>{{ draft.length }} / 2000</span>
          <button
            v-if="streaming"
            type="button"
            class="stop-button"
            @click="stopStreaming"
          >
            停止生成
          </button>
          <button
            v-else
            type="submit"
            class="send-button"
            :disabled="!draft.trim() || !activeSessionId"
          >
            发送
          </button>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createSession,
  fetchMessages,
  fetchSessions,
  removeSession,
  streamMessage,
  type ChatMessage,
  type ChatSession,
} from '../api/chat'

const starterPrompts = [
  '今天有一件事让我很难过',
  '我最近总是很累',
  '我想理一理现在的心情',
]

const sessions = ref<ChatSession[]>([])
const activeSessionId = ref<number | null>(null)
const messages = ref<ChatMessage[]>([])
const sessionsLoading = ref(true)
const messagesLoading = ref(false)
const streaming = ref(false)
const draft = ref('')
const messageArea = ref<HTMLElement | null>(null)
let streamController: AbortController | null = null
let temporaryMessageId = -1

const activeSession = computed(
  () =>
    sessions.value.find(
      (session) => session.id === activeSessionId.value,
    ) || null,
)

async function scrollToBottom() {
  await nextTick()
  if (messageArea.value) {
    messageArea.value.scrollTop = messageArea.value.scrollHeight
  }
}

async function loadSessions(selectFirst = true) {
  sessionsLoading.value = true

  try {
    sessions.value = await fetchSessions()

    if (sessions.value.length === 0) {
      const session = await createSession()
      sessions.value = [session]
    }

    if (selectFirst && activeSessionId.value === null) {
      await selectSession(sessions.value[0].id)
    }
  } catch {
    ElMessage.error('读取对话列表失败')
  } finally {
    sessionsLoading.value = false
  }
}

async function selectSession(sessionId: number) {
  if (streaming.value) {
    stopStreaming()
  }

  activeSessionId.value = sessionId
  messagesLoading.value = true

  try {
    messages.value = await fetchMessages(sessionId)
    await scrollToBottom()
  } catch {
    ElMessage.error('读取对话失败')
  } finally {
    messagesLoading.value = false
  }
}

async function newConversation() {
  if (streaming.value) {
    stopStreaming()
  }

  try {
    const session = await createSession()
    sessions.value.unshift(session)
    activeSessionId.value = session.id
    messages.value = []
    draft.value = ''
  } catch {
    ElMessage.error('创建新对话失败')
  }
}

async function sendMessage() {
  const content = draft.value.trim()

  if (!content || !activeSessionId.value || streaming.value) {
    return
  }

  const sessionId = activeSessionId.value
  const userMessage: ChatMessage = {
    id: temporaryMessageId--,
    role: 'user',
    content,
    safety_flag: false,
  }
  const assistantMessage: ChatMessage = {
    id: temporaryMessageId--,
    role: 'assistant',
    content: '',
    safety_flag: false,
  }

  messages.value.push(userMessage, assistantMessage)
  draft.value = ''
  streaming.value = true
  streamController = new AbortController()
  await scrollToBottom()

  try {
    await streamMessage(
      sessionId,
      content,
      (event) => {
        if (event.event === 'delta') {
          assistantMessage.content += event.data.content || ''
          scrollToBottom()
        } else if (event.event === 'done') {
          assistantMessage.id =
            event.data.message_id || assistantMessage.id
          assistantMessage.safety_flag =
            Boolean(event.data.safety_flag)
        } else if (event.event === 'error') {
          assistantMessage.content =
            event.data.message || '心语暂时无法回应，请稍后重试。'
        }
      },
      streamController.signal,
    )
  } catch (error) {
    if (!(error instanceof DOMException && error.name === 'AbortError')) {
      assistantMessage.content =
        error instanceof Error
          ? error.message
          : '发送消息失败，请稍后重试。'
    }
  } finally {
    streaming.value = false
    streamController = null
    await loadSessions(false)
    await scrollToBottom()
  }
}

function stopStreaming() {
  streamController?.abort()
}

async function deleteConversation() {
  if (!activeSessionId.value) {
    return
  }

  try {
    await ElMessageBox.confirm(
      '删除后这段对话将从历史记录中移除。',
      '删除对话',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
  } catch {
    return
  }

  try {
    await removeSession(activeSessionId.value)
    sessions.value = sessions.value.filter(
      (session) => session.id !== activeSessionId.value,
    )
    activeSessionId.value = null
    messages.value = []
    await loadSessions()
  } catch {
    ElMessage.error('删除对话失败')
  }
}

onMounted(loadSessions)

onBeforeUnmount(() => {
  streamController?.abort()
})
</script>

<style scoped>
.chat-layout {
  width: min(980px, 100%);
  min-height: 650px;
  display: grid;
  grid-template-columns: 230px minmax(0, 1fr);
  margin: 0 auto;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.9);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.74);
  box-shadow: 0 24px 56px rgba(120, 90, 80, 0.1);
  backdrop-filter: blur(20px);
}

.session-panel {
  padding: 20px 14px;
  border-right: 1px solid rgba(141, 110, 99, 0.1);
  background: rgba(255, 249, 247, 0.68);
}

.session-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 16px;
}

.eyebrow {
  margin: 0 0 4px;
  color: #b07f8a;
  font-size: 11px;
  letter-spacing: 0.12em;
}

.session-heading h2,
.chat-header h2 {
  margin: 0;
  color: #5d4037;
  font-size: 19px;
}

.new-chat,
.delete-chat {
  border: 1px solid #eadbd5;
  border-radius: 10px;
  padding: 7px 9px;
  color: #755b52;
  background: #fff;
  cursor: pointer;
  font-size: 12px;
}

.session-empty {
  padding: 18px 8px;
  color: #aa9188;
  font-size: 13px;
}

.session-list {
  display: grid;
  gap: 7px;
}

.session-item {
  display: grid;
  gap: 5px;
  width: 100%;
  padding: 11px 12px;
  border: 0;
  border-radius: 13px;
  text-align: left;
  color: #7c6259;
  background: transparent;
  cursor: pointer;
}

.session-item strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.session-item span {
  overflow: hidden;
  color: #aa9188;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
}

.session-item:hover,
.session-item.active {
  color: #5d4037;
  background: #fff;
}

.chat-panel {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 23px 15px;
}

.delete-chat {
  color: #a75e63;
  background: #fff7f7;
}

.safety-banner {
  margin: 0 23px 12px;
  padding: 9px 12px;
  border-radius: 11px;
  color: #8b6e61;
  background: rgba(255, 241, 224, 0.72);
  line-height: 1.6;
  font-size: 12px;
}

.message-area {
  flex: 1;
  min-height: 350px;
  max-height: 520px;
  overflow-y: auto;
  padding: 8px 23px 18px;
  scroll-behavior: smooth;
}

.empty-chat {
  max-width: 430px;
  margin: 60px auto 0;
  text-align: center;
  color: #8d746a;
}

.empty-symbol {
  width: 62px;
  height: 62px;
  display: grid;
  place-items: center;
  margin: 0 auto 14px;
  border-radius: 21px;
  color: #6d4c41;
  background: linear-gradient(135deg, #ffd7dc, #d6f1e7);
  font-size: 30px;
}

.empty-chat h3 {
  margin: 0 0 8px;
  color: #5d4037;
  font-size: 20px;
}

.empty-chat p {
  margin: 0;
  line-height: 1.7;
  font-size: 13px;
}

.prompt-list {
  display: grid;
  gap: 8px;
  margin-top: 21px;
}

.prompt-list button {
  border: 1px solid #eeded9;
  border-radius: 12px;
  padding: 10px 12px;
  color: #7c6259;
  background: #fffaf8;
  cursor: pointer;
}

.message-row {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 5px;
  margin: 0 0 15px;
}

.message-row.user {
  align-items: flex-end;
}

.message-author {
  color: #9a8177;
  font-size: 11px;
}

.message-bubble {
  max-width: min(82%, 610px);
  padding: 12px 15px;
  border-radius: 5px 17px 17px 17px;
  color: #4f3a33;
  background: #fff;
  box-shadow: 0 7px 18px rgba(120, 90, 80, 0.06);
}

.message-row.user .message-bubble {
  border-radius: 17px 5px 17px 17px;
  background: #f9dce3;
}

.message-row.safety .message-bubble {
  border: 1px solid #f0c9a7;
  background: #fff5e9;
}

.message-bubble p {
  margin: 0;
  line-height: 1.75;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.safety-label {
  display: inline-block;
  margin-top: 8px;
  padding: 3px 7px;
  border-radius: 7px;
  color: #9a5b2e;
  background: #ffead2;
  font-size: 10px;
}

.chat-composer {
  padding: 13px 23px 20px;
  border-top: 1px solid rgba(141, 110, 99, 0.1);
}

:deep(.chat-composer .el-textarea__inner) {
  border-radius: 15px;
  padding: 12px;
  color: #5d4840;
  background: #fffaf8;
  box-shadow: 0 0 0 1px #f0ded8 inset;
  line-height: 1.65;
}

.composer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 9px;
  color: #aa9188;
  font-size: 11px;
}

.send-button,
.stop-button {
  min-width: 86px;
  border: 0;
  border-radius: 11px;
  padding: 9px 16px;
  color: #5d4037;
  background: linear-gradient(135deg, #f8bbc9, #ccebdc);
  cursor: pointer;
  font-weight: 700;
}

.stop-button {
  background: #fff0ee;
}

@media (max-width: 760px) {
  .chat-layout {
    display: flex;
    flex-direction: column;
    min-height: 620px;
    border-radius: 22px;
  }

  .session-panel {
    padding: 14px;
    border-right: 0;
    border-bottom: 1px solid rgba(141, 110, 99, 0.1);
  }

  .session-heading {
    margin-bottom: 10px;
  }

  .session-list {
    display: flex;
    overflow-x: auto;
    padding-bottom: 4px;
    scrollbar-width: none;
  }

  .session-list::-webkit-scrollbar {
    display: none;
  }

  .session-item {
    flex: 0 0 155px;
  }

  .chat-header {
    padding: 16px 16px 12px;
  }

  .safety-banner {
    margin: 0 16px 10px;
  }

  .message-area {
    min-height: 330px;
    max-height: 480px;
    padding: 8px 16px 14px;
  }

  .chat-composer {
    padding: 12px 16px 17px;
  }

  .message-bubble {
    max-width: 90%;
  }
}
</style>
