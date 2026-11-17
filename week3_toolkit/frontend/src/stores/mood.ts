import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// 1. 显式定义情绪元数据接口
export interface EmotionMeta {
  emoji: string
  label: string
  color: string
  theme: string
}

export const useMoodStore = defineStore('mood', () => {
  // --- 状态定义 ---
  const currentView = ref<'capture' | 'timeline' | 'therapy'>('capture') // 视图控制
  const activeEmotion = ref<string>('')
  const confidence = ref<number>(0)
  const healingMessage = ref<string>('')

  // 2. 核心字典：使用 Record 泛型约束，取代原先的隐式推导
  const emotionDict: Record<string, EmotionMeta> = {
    happiness: { emoji: '✨', label: '开心', color: '#FFF9C4', theme: 'warm' },
    sadness: { emoji: '🍃', label: '伤心', color: '#E3F2FD', theme: 'rain' },
    surprise: { emoji: '🎈', label: '震惊', color: '#F3E5F5', theme: 'bubble' },
    fear: { emoji: '🌾', label: '害怕', color: '#ECEFF1', theme: 'fog' },
    disgust: { emoji: '🪵', label: '厌恶', color: '#E8F5E9', theme: 'isolate' },
    anger: { emoji: '🔥', label: '生气', color: '#FFEBEE', theme: 'storm' },
    neutral: { emoji: '😌', label: '平静', color: '#E8F5E9', theme: 'calm' }
  }

  // --- Getters ---
  // 3. 优雅取值：去掉了强行 as keyof typeof 的断言，且明确返回值类型为 EmotionMeta
  const currentEmotionMeta = computed<EmotionMeta>(() => {
    return emotionDict[activeEmotion.value] || {
      emoji: '✨',
      label: '感知中',
      color: '#FFFFFF',
      theme: 'default'
    }
  })

  // --- Actions (业务逻辑) ---
  function setEmotion(emo: string, conf: number, msg: string) {
    activeEmotion.value = emo.toLowerCase()
    confidence.value = conf
    healingMessage.value = msg
  }

  function resetEmotion() {
    activeEmotion.value = ''
    confidence.value = 0
    healingMessage.value = ''
  }

  return {
    currentView,
    activeEmotion,
    confidence,
    healingMessage,
    currentEmotionMeta,
    emotionDict,
    setEmotion,
    resetEmotion
  }
})