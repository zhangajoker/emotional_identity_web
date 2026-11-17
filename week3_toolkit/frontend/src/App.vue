<template>
  <div class="app-container">
    <FloatingBackground />

    <header class="header">
      <h1>✨ 情绪感知日记</h1>
      <p class="subtitle">无论是哪种心情，都值得被温柔以待</p>
    </header>

    <main class="main-content">
      <div class="main-nav">
        <el-radio-group v-model="moodStore.currentView" size="large">
          <el-radio-button label="capture">🧭 情绪感知</el-radio-button>
          <el-radio-button label="timeline">⏳ 时光长廊</el-radio-button>
          <el-radio-button label="therapy">🧘 呼吸疗愈</el-radio-button>
        </el-radio-group>
      </div>

      <div v-if="moodStore.currentView === 'capture'" class="view-section">
        <div class="healing-card interact-area">

          <div class="mode-switcher">
            <el-radio-group v-model="inputMode" @change="handleModeChange">
              <el-radio-button label="upload">文件上传</el-radio-button>
              <el-radio-button label="camera">实时摄像头</el-radio-button>
            </el-radio-group>
          </div>

          <div v-if="inputMode === 'camera'" class="preview-wrapper">
            <div class="media-container">
              <video ref="cameraVideoRef" autoplay playsinline muted class="preview-media"></video>
              <canvas ref="cameraCanvasRef" class="overlay-canvas"></canvas>
            </div>
            <p class="live-tip">🎥 正在实时捕捉您的面部表情...</p>
          </div>

          <el-upload
            v-if="inputMode === 'upload'"
            class="emotion-uploader"
            drag
            action="#"
            :auto-upload="false"
            :on-change="handleFileChange"
            :show-file-list="false"
            accept="image/*,video/mp4,video/quicktime,video/webm"
          >
            <div v-if="fileUrl" class="preview-wrapper">
              <img v-if="fileType === 'image'" :src="fileUrl" class="preview-media" alt="你的照片" />

              <div v-else-if="fileType === 'video'" class="media-container">
                <video
                  ref="uploadVideoRef"
                  :src="fileUrl"
                  controls
                  playsinline
                  class="preview-media"
                  @play="startVideoTracking"
                  @pause="stopVideoTracking"
                  @ended="stopVideoTracking"
                ></video>
                <canvas ref="uploadCanvasRef" class="overlay-canvas"></canvas>
              </div>
            </div>
            <div v-else class="upload-placeholder">
              <el-icon class="el-icon--upload"><Picture /></el-icon>
              <div class="el-upload__text">
                点击或拖拽上传照片/视频，<br/>让我感受你此刻的心情
              </div>
            </div>
          </el-upload>

          <div class="action-bar" v-if="inputMode === 'upload' && fileType === 'image'">
            <el-button type="primary" size="large" @click="analyzeStaticImage" :loading="isAnalyzing">
              {{ isAnalyzing ? '正在用心感受中...' : '开始解读照片' }}
            </el-button>
          </div>
          <div class="action-bar" v-else-if="inputMode === 'upload' && fileType === 'video'">
            <p class="live-tip">▶️ 点击播放视频，系统将自动进行追踪解读</p>
          </div>
        </div>

        <div class="healing-card result-area" v-if="moodStore.activeEmotion">
          <h2 class="emotion-title">当前感知到的情绪是...</h2>

          <div class="emotion-display">
            <span class="emoji">{{ moodStore.currentEmotionMeta.emoji }}</span>
            <span class="emotion-name">{{ moodStore.currentEmotionMeta.label }}</span>
          </div>

          <div class="confidence-display" v-if="moodStore.confidence > 0">
            模型确定度: {{ moodStore.confidence }}%
          </div>

          <p class="healing-message" v-if="showBigEmoji">{{ moodStore.healingMessage }}</p>
        </div>

        <JournalInputLayer v-if="moodStore.activeEmotion" />
      </div>

      <div v-else-if="moodStore.currentView === 'timeline'" class="view-section">
        <MoodTimelineView />
      </div>

      <div v-else-if="moodStore.currentView === 'therapy'" class="view-section">
        <CbtBreathingTherapy />
      </div>
    </main>

    <EmotionEffects :emotion="showBigEmoji ? moodStore.activeEmotion : ''" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount } from 'vue'
import { Picture } from '@element-plus/icons-vue'
import axios from 'axios'
import { useMoodStore } from './stores/mood' // 引入系统神经中枢

import FloatingBackground from './components/FloatingBackground.vue'
import EmotionEffects from './components/EmotionEffects.vue'
import JournalInputLayer from './components/JournalInputLayer.vue'
import MoodTimelineView from './components/MoodTimelineView.vue'
import CbtBreathingTherapy from './components/CbtBreathingTherapy.vue'

// 初始化全局状态
const moodStore = useMoodStore()

// ================= 基础状态 =================
const inputMode = ref<'upload' | 'camera'>('upload')
const fileUrl = ref<string>('')
const currentFile = ref<File | null>(null)
const fileType = ref<'image' | 'video' | null>(null)
const isAnalyzing = ref<boolean>(false)

// DOM 引用
const cameraVideoRef = ref<HTMLVideoElement | null>(null)
const cameraCanvasRef = ref<HTMLCanvasElement | null>(null)
const uploadVideoRef = ref<HTMLVideoElement | null>(null)
const uploadCanvasRef = ref<HTMLCanvasElement | null>(null)

// 追踪器状态
let cameraStream: MediaStream | null = null
let cameraInterval: number | null = null
let videoInterval: number | null = null
let isProcessingFrame = false

// 核心计算属性：是否允许全屏大动画？
const showBigEmoji = computed(() => {
  return inputMode.value === 'upload' && fileType.value === 'image'
})

// ================= 交互逻辑 =================
const handleModeChange = (mode: string) => {
  moodStore.resetEmotion() // 切换模式时清空状态
  if (mode === 'camera') {
    startCamera()
  } else {
    stopCamera()
  }
}

const handleFileChange = (file: any) => {
  const rawFile = file.raw as File
  if (fileUrl.value) URL.revokeObjectURL(fileUrl.value)

  fileUrl.value = URL.createObjectURL(rawFile)
  currentFile.value = rawFile
  fileType.value = rawFile.type.startsWith('video/') ? 'video' : 'image'

  moodStore.resetEmotion() // 换新文件时清空状态
  stopVideoTracking()
}

// ================= 抽帧与画框核心逻辑 =================
const processFrame = async (video: HTMLVideoElement, overlay: HTMLCanvasElement) => {
  if (video.paused || video.ended || video.readyState !== 4 || isProcessingFrame) return
  isProcessingFrame = true

  if (overlay.width !== video.videoWidth || overlay.height !== video.videoHeight) {
    overlay.width = video.videoWidth
    overlay.height = video.videoHeight
  }

  const offscreen = document.createElement('canvas')
  offscreen.width = video.videoWidth
  offscreen.height = video.videoHeight
  const ctx = offscreen.getContext('2d')
  if (!ctx) { isProcessingFrame = false; return }

  ctx.drawImage(video, 0, 0, offscreen.width, offscreen.height)

  offscreen.toBlob(async (blob) => {
    if (!blob) { isProcessingFrame = false; return }
    const formData = new FormData()
    formData.append('file', blob, 'frame.jpg')

    try {
      const response = await axios.post('http://localhost:8000/api/analyze', formData)
      const oCtx = overlay.getContext('2d')
      if (!oCtx) return

      oCtx.clearRect(0, 0, overlay.width, overlay.height)

      if (response.data.status === 'success') {
        const data = response.data.data
        const box = data.face_box
        const emo = data.emotion.toLowerCase()
        const conf = data.confidence

        // 同步给 Pinia 状态树
        moodStore.setEmotion(emo, conf, data.message)

        oCtx.strokeStyle = '#00E676'
        oCtx.lineWidth = Math.max(3, overlay.width / 200)
        oCtx.strokeRect(box.x1, box.y1, box.x2 - box.x1, box.y2 - box.y1)

        // 动态读取字典里的 label
        const labelText = `${moodStore.emotionDict[emo]?.label || emo} ${conf}%`
        const fontSize = Math.max(16, overlay.width / 35)
        oCtx.font = `bold ${fontSize}px sans-serif`

        const padding = 6
        const textWidth = oCtx.measureText(labelText).width
        const textHeight = fontSize + 4

        oCtx.fillStyle = '#00E676'
        oCtx.fillRect(box.x1, box.y1 - textHeight - padding * 2, textWidth + padding * 2, textHeight + padding * 2)

        oCtx.fillStyle = '#FFFFFF'
        oCtx.textBaseline = 'top'
        oCtx.fillText(labelText, box.x1 + padding, box.y1 - textHeight - padding)
      }
    } catch (error) {
    } finally {
      isProcessingFrame = false
    }
  }, 'image/jpeg', 0.8)
}

// ================= 摄像头控制 =================
const startCamera = async () => {
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480 }
    })
    if (cameraVideoRef.value) {
      cameraVideoRef.value.srcObject = cameraStream
      cameraVideoRef.value.play()

      cameraInterval = window.setInterval(() => {
        if (cameraVideoRef.value && cameraCanvasRef.value) {
          processFrame(cameraVideoRef.value, cameraCanvasRef.value)
        }
      }, 500)
    }
  } catch (error) {
    alert("无法调用摄像头，请检查浏览器权限哦~")
    inputMode.value = 'upload'
  }
}

const stopCamera = () => {
  if (cameraStream) {
    cameraStream.getTracks().forEach(track => track.stop())
    cameraStream = null
  }
  if (cameraInterval) {
    clearInterval(cameraInterval)
    cameraInterval = null
  }
  if (cameraCanvasRef.value) {
    cameraCanvasRef.value.getContext('2d')?.clearRect(0, 0, 9999, 9999)
  }
}

// ================= 本地视频控制 =================
const startVideoTracking = () => {
  if (videoInterval) clearInterval(videoInterval)
  videoInterval = window.setInterval(() => {
    if (uploadVideoRef.value && uploadCanvasRef.value) {
      processFrame(uploadVideoRef.value, uploadCanvasRef.value)
    }
  }, 500)
}

const stopVideoTracking = () => {
  if (videoInterval) clearInterval(videoInterval)
  videoInterval = null
}

// ================= 静态照片专属请求 =================
const analyzeStaticImage = async () => {
  if (!currentFile.value) return
  isAnalyzing.value = true
  moodStore.resetEmotion() // 请求前重置

  const formData = new FormData()
  formData.append('file', currentFile.value)

  try {
    const response = await axios.post('http://localhost:8000/api/analyze', formData)
    if (response.data.status === 'success') {
      let emo = response.data.data.emotion.toLowerCase()
      // 同步给 Pinia 状态树
      moodStore.setEmotion(emo, response.data.data.confidence, response.data.data.message)
    } else {
      alert(response.data.message)
    }
  } catch (error) {
    alert("系统遇到了一点小麻烦，请稍后再试。")
  } finally {
    isAnalyzing.value = false
  }
}

onBeforeUnmount(() => {
  stopCamera()
  stopVideoTracking()
})
</script>

<style scoped>
/* 原汁原味的居中与定宽设计 */
.app-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 40px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  z-index: 1;
}

.header { text-align: center; margin-bottom: 40px; }
.header h1 { font-size: 2.5rem; color: var(--text-main); margin-bottom: 10px; }
.subtitle { color: var(--text-light); font-size: 1.1rem; }

.main-content {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 30px;
}

/* 导航栏样式 */
.main-nav {
  display: flex;
  justify-content: center;
  margin-bottom: 10px;
}

/* 视图切换容器与动画 */
.view-section {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 30px;
  animation: fadeIn 0.5s ease-out;
}

.mode-switcher { margin-bottom: 15px; text-align: center; }

/* 画布叠加核心样式 */
.media-container {
  position: relative;
  display: flex;
  justify-content: center;
  width: 100%;
  max-width: 100%;
  margin: 0 auto;
}

.preview-media {
  display: block;
  max-width: 100%;
  max-height: 450px;
  width: auto;
  height: auto;
  border-radius: 12px;
}

.overlay-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.emotion-uploader { border-radius: var(--radius-large); overflow: hidden; }
.upload-placeholder { display: flex; flex-direction: column; align-items: center; color: var(--text-light); }
.preview-wrapper { width: 100%; display: flex; flex-direction: column; align-items: center; }

.action-bar { margin-top: 25px; text-align: center; }
.live-tip { margin-top: 15px; color: var(--text-light); font-size: 0.95rem; }

.result-area { text-align: center; animation: fadeIn 0.8s ease-out; }
.emotion-title { font-size: 1.2rem; color: var(--text-light); margin-bottom: 20px; }
.emotion-display { display: flex; align-items: center; justify-content: center; gap: 15px; margin-bottom: 10px; }
.emoji { font-size: 4rem; }
.emotion-name { font-size: 2rem; font-weight: bold; color: var(--text-main); }
.confidence-display { color: var(--text-light); margin-bottom: 20px; font-size: 0.95rem; background: rgba(255, 255, 255, 0.5); display: inline-block; padding: 4px 12px; border-radius: 12px; }
.healing-message { font-size: 1.1rem; line-height: 1.6; color: var(--text-main); background-color: var(--bg-color); padding: 15px 25px; border-radius: 12px; display: inline-block; }

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>