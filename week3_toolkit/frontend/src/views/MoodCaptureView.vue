<template>
  <section class="capture-view">
    <div class="healing-card interact-area">
      <div class="mode-switcher">
        <el-radio-group v-model="inputMode" @change="handleModeChange">
          <el-radio-button label="upload">文件上传</el-radio-button>
          <el-radio-button label="camera">实时摄像头</el-radio-button>
        </el-radio-group>
      </div>

      <div v-if="inputMode === 'camera'" class="preview-wrapper">
        <div class="media-container">
          <video
            ref="cameraVideoRef"
            autoplay
            playsinline
            muted
            class="preview-media"
          ></video>
          <canvas ref="cameraCanvasRef" class="overlay-canvas"></canvas>
        </div>
        <p class="live-tip">正在实时捕捉你的面部表情...</p>
      </div>

      <el-upload
        v-if="inputMode === 'upload'"
        class="emotion-uploader"
        drag
        action="#"
        :auto-upload="false"
        :on-change="handleFileChange"
        :show-file-list="false"
        accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/webm"
      >
        <div v-if="fileUrl" class="preview-wrapper">
          <img
            v-if="fileType === 'image'"
            :src="fileUrl"
            class="preview-media"
            alt="你上传的照片"
          />

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
            点击或拖拽上传照片/视频<br />
            让我感受你此刻的心情
          </div>
        </div>
      </el-upload>

      <div
        v-if="inputMode === 'upload' && fileType === 'image'"
        class="action-bar"
      >
        <el-button
          type="primary"
          size="large"
          :loading="isAnalyzing"
          @click="analyzeStaticImage"
        >
          {{ isAnalyzing ? '正在解读照片...' : '开始解读照片' }}
        </el-button>
      </div>

      <div
        v-else-if="inputMode === 'upload' && fileType === 'video'"
        class="action-bar"
      >
        <p class="live-tip">点击播放视频，系统会自动进行追踪解读</p>
      </div>
    </div>

    <div v-if="moodStore.activeEmotion" class="healing-card result-area">
      <h2 class="emotion-title">当前感知到的情绪是...</h2>

      <div class="emotion-display">
        <span class="emoji">{{ moodStore.currentEmotionMeta.emoji }}</span>
        <span class="emotion-name">
          {{ moodStore.currentEmotionMeta.label }}
        </span>
      </div>

      <div v-if="moodStore.confidence > 0" class="confidence-display">
        模型确定度：{{ moodStore.confidence }}%
      </div>

      <p v-if="showBigEmoji" class="healing-message">
        {{ moodStore.healingMessage }}
      </p>
    </div>

    <JournalInputLayer v-if="moodStore.activeEmotion" />

    <EmotionEffects
      :emotion="showBigEmoji ? moodStore.activeEmotion : ''"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { Picture } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../api/client'
import { useMoodStore } from '../stores/mood'
import EmotionEffects from '../components/EmotionEffects.vue'
import JournalInputLayer from '../components/JournalInputLayer.vue'

const moodStore = useMoodStore()

const inputMode = ref<'upload' | 'camera'>('upload')
const fileUrl = ref('')
const currentFile = ref<File | null>(null)
const fileType = ref<'image' | 'video' | null>(null)
const isAnalyzing = ref(false)

const MAX_IMAGE_BYTES = 10 * 1024 * 1024
const MAX_VIDEO_BYTES = 50 * 1024 * 1024
const ALLOWED_IMAGE_TYPES = new Set([
  'image/jpeg',
  'image/png',
  'image/webp',
])
const ALLOWED_VIDEO_TYPES = new Set([
  'video/mp4',
  'video/quicktime',
  'video/webm',
])

const cameraVideoRef = ref<HTMLVideoElement | null>(null)
const cameraCanvasRef = ref<HTMLCanvasElement | null>(null)
const uploadVideoRef = ref<HTMLVideoElement | null>(null)
const uploadCanvasRef = ref<HTMLCanvasElement | null>(null)

let cameraStream: MediaStream | null = null
let cameraInterval: number | null = null
let videoInterval: number | null = null
let isProcessingFrame = false

const showBigEmoji = computed(
  () => inputMode.value === 'upload' && fileType.value === 'image',
)

function handleModeChange(mode: string) {
  moodStore.resetEmotion()

  if (mode === 'camera') {
    startCamera()
  } else {
    stopCamera()
  }
}

function handleFileChange(file: any) {
  const rawFile = file.raw as File | undefined

  if (!rawFile) {
    return
  }

  if (rawFile.size === 0) {
    ElMessage.error('所选文件是空文件')
    return
  }

  const isImage = ALLOWED_IMAGE_TYPES.has(rawFile.type)
  const isVideo = ALLOWED_VIDEO_TYPES.has(rawFile.type)

  if (!isImage && !isVideo) {
    ElMessage.error('仅支持 JPG、PNG、WebP、MP4、MOV 或 WebM')
    return
  }

  const maxBytes = isImage ? MAX_IMAGE_BYTES : MAX_VIDEO_BYTES

  if (rawFile.size > maxBytes) {
    ElMessage.error(`文件不能超过 ${isImage ? '10MB' : '50MB'}`)
    return
  }

  if (fileUrl.value) {
    URL.revokeObjectURL(fileUrl.value)
  }

  fileUrl.value = URL.createObjectURL(rawFile)
  currentFile.value = rawFile
  fileType.value = isImage ? 'image' : 'video'

  moodStore.resetEmotion()
  stopVideoTracking()
}

async function processFrame(
  video: HTMLVideoElement,
  overlay: HTMLCanvasElement,
) {
  if (
    video.paused ||
    video.ended ||
    video.readyState !== 4 ||
    isProcessingFrame
  ) {
    return
  }

  isProcessingFrame = true

  if (overlay.width !== video.videoWidth || overlay.height !== video.videoHeight) {
    overlay.width = video.videoWidth
    overlay.height = video.videoHeight
  }

  const offscreen = document.createElement('canvas')
  offscreen.width = video.videoWidth
  offscreen.height = video.videoHeight
  const context = offscreen.getContext('2d')

  if (!context) {
    isProcessingFrame = false
    return
  }

  context.drawImage(video, 0, 0, offscreen.width, offscreen.height)

  offscreen.toBlob(
    async (blob) => {
      if (!blob) {
        isProcessingFrame = false
        return
      }

      const formData = new FormData()
      formData.append('file', blob, 'frame.jpg')

      try {
        const response = await api.post('/analyze', formData)
        const overlayContext = overlay.getContext('2d')

        if (!overlayContext) {
          return
        }

        overlayContext.clearRect(0, 0, overlay.width, overlay.height)

        if (response.data.status === 'success') {
          const data = response.data.data
          const box = data.face_box
          const emotion = data.emotion.toLowerCase()
          const confidence = data.confidence

          moodStore.setEmotion(emotion, confidence, data.message)

          overlayContext.strokeStyle = '#00E676'
          overlayContext.lineWidth = Math.max(3, overlay.width / 200)
          overlayContext.strokeRect(
            box.x1,
            box.y1,
            box.x2 - box.x1,
            box.y2 - box.y1,
          )

          const labelText =
            `${moodStore.emotionDict[emotion]?.label || emotion} ` +
            `${confidence}%`
          const fontSize = Math.max(16, overlay.width / 35)
          overlayContext.font = `bold ${fontSize}px sans-serif`

          const padding = 6
          const textWidth = overlayContext.measureText(labelText).width
          const textHeight = fontSize + 4

          overlayContext.fillStyle = '#00E676'
          overlayContext.fillRect(
            box.x1,
            box.y1 - textHeight - padding * 2,
            textWidth + padding * 2,
            textHeight + padding * 2,
          )

          overlayContext.fillStyle = '#FFFFFF'
          overlayContext.textBaseline = 'top'
          overlayContext.fillText(
            labelText,
            box.x1 + padding,
            box.y1 - textHeight - padding,
          )
        }
      } catch {
        // 实时帧失败时跳过，下一帧会继续尝试。
      } finally {
        isProcessingFrame = false
      }
    },
    'image/jpeg',
    0.8,
  )
}

async function startCamera() {
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480 },
    })

    if (!cameraVideoRef.value) {
      return
    }

    cameraVideoRef.value.srcObject = cameraStream
    await cameraVideoRef.value.play()

    cameraInterval = window.setInterval(() => {
      if (cameraVideoRef.value && cameraCanvasRef.value) {
        processFrame(cameraVideoRef.value, cameraCanvasRef.value)
      }
    }, 500)
  } catch {
    ElMessage.error('无法调用摄像头，请检查浏览器权限或使用 HTTPS')
    inputMode.value = 'upload'
  }
}

function stopCamera() {
  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop())
    cameraStream = null
  }

  if (cameraInterval) {
    clearInterval(cameraInterval)
    cameraInterval = null
  }

  cameraCanvasRef.value
    ?.getContext('2d')
    ?.clearRect(0, 0, 9999, 9999)
}

function startVideoTracking() {
  if (videoInterval) {
    clearInterval(videoInterval)
  }

  videoInterval = window.setInterval(() => {
    if (uploadVideoRef.value && uploadCanvasRef.value) {
      processFrame(uploadVideoRef.value, uploadCanvasRef.value)
    }
  }, 500)
}

function stopVideoTracking() {
  if (videoInterval) {
    clearInterval(videoInterval)
  }

  videoInterval = null
}

async function analyzeStaticImage() {
  if (!currentFile.value) {
    return
  }

  isAnalyzing.value = true
  moodStore.resetEmotion()

  const formData = new FormData()
  formData.append('file', currentFile.value)

  try {
    const response = await api.post('/analyze', formData)

    if (response.data.status === 'success') {
      moodStore.setEmotion(
        response.data.data.emotion.toLowerCase(),
        response.data.data.confidence,
        response.data.data.message,
      )
    } else {
      ElMessage.error(response.data.message)
    }
  } catch {
    ElMessage.error('系统遇到了一点小麻烦，请稍后再试')
  } finally {
    isAnalyzing.value = false
  }
}

onBeforeUnmount(() => {
  stopCamera()
  stopVideoTracking()

  if (fileUrl.value) {
    URL.revokeObjectURL(fileUrl.value)
  }
})
</script>

<style scoped>
.capture-view {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.mode-switcher {
  margin-bottom: 15px;
  text-align: center;
}

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
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.emotion-uploader {
  border-radius: var(--radius-large);
  overflow: hidden;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: var(--text-light);
}

.preview-wrapper {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.action-bar {
  margin-top: 25px;
  text-align: center;
}

.live-tip {
  margin-top: 15px;
  color: var(--text-light);
  font-size: 0.95rem;
}

.result-area {
  text-align: center;
  animation: fadeIn 0.8s ease-out;
}

.emotion-title {
  font-size: 1.2rem;
  color: var(--text-light);
  margin-bottom: 20px;
}

.emotion-display {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  margin-bottom: 10px;
}

.emoji {
  font-size: 4rem;
}

.emotion-name {
  font-size: 2rem;
  font-weight: bold;
  color: var(--text-main);
}

.confidence-display {
  color: var(--text-light);
  margin-bottom: 20px;
  font-size: 0.95rem;
  background: rgba(255, 255, 255, 0.5);
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
}

.healing-message {
  font-size: 1.1rem;
  line-height: 1.6;
  color: var(--text-main);
  background-color: var(--bg-color);
  padding: 15px 25px;
  border-radius: 12px;
  display: inline-block;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 600px) {
  .preview-media {
    max-height: 340px;
  }

  .emotion-name {
    font-size: 1.55rem;
  }
}
</style>
