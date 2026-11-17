<template>
  <div class="cbt-journal-card">
    <div class="header-badge">
      <span class="avatar-emoji">{{ moodStore.currentEmotionMeta.emoji }}</span>
      <div class="title-meta">
        <h4>当下状态：{{ moodStore.currentEmotionMeta.label }}</h4>
        <p>客观置信概率：{{ moodStore.confidence }}%</p>
      </div>
    </div>

    <blockquote class="resonance-bubble">
      "{{ moodStore.healingMessage }}"
    </blockquote>

    <div class="cbt-form">
      <label class="input-label">🧠 记录这一刻发生的事实（客观诱因）：</label>
      <el-input
        v-model="form.fact"
        type="textarea"
        :rows="2"
        placeholder="发生了什么，让你产生了当前的情绪反应..."
        resize="none"
        class="therapy-field"
      />

      <label class="input-label" v-if="isNegativeMood">💡 此时脑海里闪过的第一想法（主观执念）：</label>
      <el-input
        v-if="isNegativeMood"
        v-model="form.thought"
        type="textarea"
        :rows="2"
        placeholder="倾听心底最真实、哪怕有些任性的委屈..."
        resize="none"
        class="therapy-field"
      />

      <label class="input-label">✍️ 留给未来的微便签：</label>
      <el-input
        v-model="form.notes"
        type="textarea"
        :rows="2"
        placeholder="写一句对自己说的话吧..."
        resize="none"
        class="therapy-field"
      />
    </div>

    <div class="submit-tray">
      <el-button class="cancel-btn" @click="moodStore.resetEmotion">释放本次</el-button>
      <el-button type="success" :loading="submitting" @click="commitDiary" class="commit-btn">
        🔐 温柔封存至多维足迹
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useMoodStore } from '../stores/mood'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const moodStore = useMoodStore()
const submitting = ref(false)

const form = ref({
  fact: '',
  thought: '',
  notes: ''
})

const isNegativeMood = computed(() => {
  return ['sadness', 'anger', 'fear', 'disgust'].includes(moodStore.activeEmotion)
})

const commitDiary = async () => {
  submitting.value = true
  try {
    // 聚合多模态文本字段，构成完整的认知重述内容
    const structuredText = `【客观测度事实】: ${form.value.fact || '未阐述'}\n` +
                           (isNegativeMood.value ? `【底层潜意识主观思维】: ${form.value.thought || '未阐述'}\n` : '') +
                           `【自我关怀寄语】: ${form.value.notes || '心如止水'}`

    const payload = {
      visual_emotion: moodStore.activeEmotion,
      confidence: moodStore.confidence,
      text_content: structuredText,
      healing_message: moodStore.healingMessage
    }

    const res = await axios.post('http://localhost:8000/api/diary', payload)
    if (res.data.status === 'success') {
      ElMessage.success('您的心流手账已被数字网络温柔加密保管。')
      // 重置表单与总线
      form.value = { fact: '', thought: '', notes: '' }
      moodStore.resetEmotion()
      // 优雅跳转到时光长廊
      moodStore.currentView = 'timeline'
    }
  } catch {
    ElMessage.error('封存失败，时空隧道发生抖动。')
  } finally { submitting.value = false }
}
</script>

<style scoped>
.cbt-journal-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border-radius: 32px;
  padding: 35px;
  box-shadow: 0 30px 60px rgba(15, 23, 42, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.7);
}
.header-badge { display: flex; align-items: center; gap: 20px; margin-bottom: 25px; }
.avatar-emoji { font-size: 3rem; background: #fff; padding: 10px; border-radius: 20px; box-shadow: 0 10px 20px rgba(0,0,0,0.02); }
.title-meta h4 { margin: 0 0 5px 0; font-size: 1.25rem; color: #1e293b; }
.title-meta p { margin: 0; font-size: 0.85rem; color: #94a3b8; }
.resonance-bubble {
  background: #f8fafc; border-left: 5px solid #a8e6cf; padding: 15px 20px; margin: 0 0 30px 0;
  font-style: italic; color: #475569; font-size: 0.95rem; border-radius: 4px 16px 16px 4px; line-height: 1.6;
}
.cbt-form { display: flex; flex-direction: column; gap: 12px; }
.input-label { font-size: 0.88rem; font-weight: 600; color: #475569; margin-top: 10px; }
:deep(.therapy-field .el-textarea__inner) {
  border-radius: 14px; background: #fafafa; border-color: #e2e8f0; padding: 12px; transition: all 0.3s;
}
:deep(.therapy-field .el-textarea__inner:focus) { background: #fff; border-color: #a8e6cf; box-shadow: 0 0 0 3px rgba(168,230,207,0.2); }
.submit-tray { display: flex; justify-content: space-between; margin-top: 30px; }
.cancel-btn { border-radius: 20px; border: 1px solid #e2e8f0; }
.commit-btn { background-color: #a8e6cf !important; border: none !important; color: #1e293b !important; font-weight: bold; border-radius: 20px; padding: 12px 24px; }
</style>