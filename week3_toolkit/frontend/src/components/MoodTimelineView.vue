<template>
  <div class="timeline-container">
    <div class="timeline-header">
      <h3>⏳ 情感数字长廊</h3>
      <p>这里留存了你在整个时空中每一次呼吸的心灵回响</p>
    </div>

    <div v-if="loading" class="center-loading">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else-if="list.length === 0" class="empty-state">
      <p>长廊里还没有故事，去感知舱留下你的第一张快照吧 ✨</p>
    </div>

    <div v-else class="timeline-scroll-area">
      <el-timeline>
        <el-timeline-item
          v-for="item in list"
          :key="item.id"
          :timestamp="item.formatted_time"
          placement="top"
          type="primary"
          class="custom-node"
        >
          <div
            class="diary-asset-card"
            :style="{ background: moodStore.emotionDict[item.visual_emotion as keyof typeof moodStore.emotionDict]?.color || '#fff' }"
          >
            <div class="card-top">
              <span class="card-emoji">
                {{ moodStore.emotionDict[item.visual_emotion as keyof typeof moodStore.emotionDict]?.emoji || '🍃' }}
              </span>
              <div class="card-headline">
                <h4>判定状态：{{ moodStore.emotionDict[item.visual_emotion as keyof typeof moodStore.emotionDict]?.label || item.visual_emotion }}</h4>
                <p class="asset-confidence">确信度：{{ item.confidence }}%</p>
              </div>
            </div>

            <div class="card-content">
              <p class="raw-text">{{ item.text_content }}</p>
            </div>

            <div class="card-quote">
              <span class="quote-icon">“</span>
              <p>{{ item.healing_message }}</p>
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useMoodStore } from '../stores/mood'
import { api } from '../api/client'

const moodStore = useMoodStore()
const list = ref<any[]>([])
const loading = ref(true)

const fetchHistory = async () => {
  try {
    const res = await api.get('/diary/history')
    if (res.data.status === 'success') {
      list.value = res.data.data
    }
  } catch { } finally { loading.value = false }
}

onMounted(fetchHistory)
</script>

<style scoped>
.timeline-container { max-width: 750px; margin: 0 auto; animation: fadeIn 0.5s ease; }
.timeline-header { text-align: center; margin-bottom: 40px; }
.timeline-header h3 { font-size: 1.8rem; color: #1e293b; margin-bottom: 8px; }
.timeline-header p { color: #64748b; font-size: 0.95rem; }
.timeline-scroll-area { max-height: 70vh; overflow-y: auto; padding-right: 15px; }

/* 深度定制组件卡片 */
.diary-asset-card {
  border-radius: 24px; padding: 25px; transition: all 0.3s;
  box-shadow: 0 10px 25px rgba(0,0,0,0.02); border: 1px solid rgba(255,255,255,0.6);
}
.diary-asset-card:hover { transform: translateY(-4px); box-shadow: 0 15px 35px rgba(0,0,0,0.06); }
.card-top { display: flex; align-items: center; gap: 15px; margin-bottom: 15px; }
.card-emoji { font-size: 2.2rem; background: rgba(255,255,255,0.6); padding: 6px; border-radius: 12px; }
.card-headline h4 { margin: 0; color: #1e293b; font-size: 1.1rem; }
.card-headline p { margin: 3px 0 0 0; font-size: 0.8rem; color: #64748b; }
.card-content { background: rgba(255,255,255,0.4); padding: 15px; border-radius: 14px; margin-bottom: 15px; }
.raw-text { margin: 0; line-height: 1.6; color: #334155; white-space: pre-line; font-size: 0.95rem; }
.card-quote { display: flex; gap: 8px; font-style: italic; color: #475569; font-size: 0.88rem; line-height: 1.5; }
.quote-icon { font-size: 1.5rem; line-height: 1; color: #cbd5e1; }
.empty-state { text-align: center; color: #94a3b8; padding: 100px 0; }

/* 隐藏自带的原生纵向滚动条，保持精致 */
.timeline-scroll-area::-webkit-scrollbar { width: 6px; }
.timeline-scroll-area::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.05); border-radius: 10px; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
</style>