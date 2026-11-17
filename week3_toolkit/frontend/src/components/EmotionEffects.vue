<template>
  <div class="sticker-container" v-if="isActive">
    <div class="sticker-emoji" :class="animationClass">
      {{ activeEmoji }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  emotion: string
}>()

// 状态控制
const isActive = ref(false)
const activeEmoji = ref('')
const animationClass = ref('')
let timer: number | null = null

// 情绪对应的超级大表情包 (可以替换成你喜欢的任何 Emoji)
const stickerMap: Record<string, string> = {
  happiness: '😍',
  sadness: '😭',
  surprise: '🤯',
  fear: '😱',
  disgust: '🤢',
  anger: '😡',
  neutral: '🍃'
}

// 核心逻辑：给不同的情绪分配不同的“弹出动画”
const getAnimationClass = (emo: string) => {
  if (emo === 'anger') return 'anim-shake-pop'  // 愤怒：带震动和气炸的效果
  if (emo === 'sadness') return 'anim-drop-fade' // 难过：沉重下坠的效果
  return 'anim-bounce-pop'                       // 其他：常规的 Q弹放大效果
}

// 监听父组件的情绪变化
watch(() => props.emotion, (newVal) => {
  if (!newVal) return

  // 防止连续点击导致动画重叠，先清除定时器
  if (timer) clearTimeout(timer)

  // 设置当前表情和对应的动画类
  activeEmoji.value = stickerMap[newVal] || '✨'
  animationClass.value = getAnimationClass(newVal)

  // 触发 DOM 渲染
  isActive.value = true

  // 1.2秒后自动卸载该 DOM，完全释放性能 (符合你要求的 0.5 - 1.5秒)
  timer = window.setTimeout(() => {
    isActive.value = false
  }, 1200)
})
</script>

<style scoped>
.sticker-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  /* 确保表情包在绝对的屏幕正中央 */
  display: flex;
  justify-content: center;
  align-items: center;
  pointer-events: none; /* 绝对不能阻挡用户的点击操作 */
  z-index: 9999; /* 放在最高层级 */
}

/* 表情包本体样式 */
.sticker-emoji {
  font-size: 12rem; /* 约 192px，超大号视觉冲击 */
  filter: drop-shadow(0 15px 25px rgba(0, 0, 0, 0.25)); /* 立体阴影 */
  will-change: transform, opacity; /* 开启 GPU 硬件加速，绝对丝滑 */
}

/* =========================================
   动画 1：通用 Q 弹放大弹出 (Happiness, Surprise 等)
========================================= */
.anim-bounce-pop {
  animation: bouncePop 1.2s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
}

@keyframes bouncePop {
  0% { transform: scale(0.2); opacity: 0; }
  20% { transform: scale(1.2); opacity: 1; }
  30% { transform: scale(1); opacity: 1; }
  80% { transform: scale(1); opacity: 1; }
  100% { transform: scale(1.5); opacity: 0; } /* 放大淡出 */
}

/* =========================================
   动画 2：愤怒专属 (Anger) - 气得发抖弹出
========================================= */
.anim-shake-pop {
  animation: shakePop 1.2s ease-in-out forwards;
}

@keyframes shakePop {
  0% { transform: scale(0.2); opacity: 0; }
  15% { transform: scale(1.3); opacity: 1; }
  25% { transform: scale(1) rotate(-15deg); opacity: 1; }
  35% { transform: scale(1.1) rotate(15deg); opacity: 1; }
  45% { transform: scale(1) rotate(-10deg); opacity: 1; }
  55% { transform: scale(1.05) rotate(10deg); opacity: 1; }
  65% { transform: scale(1) rotate(0deg); opacity: 1; }
  80% { transform: scale(1); opacity: 1; }
  100% { transform: scale(1.5); opacity: 0; filter: blur(4px); } /* 气炸了模糊消失 */
}

/* =========================================
   动画 3：难过专属 (Sadness) - 沉重下坠
========================================= */
.anim-drop-fade {
  animation: dropFade 1.2s ease-in forwards;
}

@keyframes dropFade {
  0% { transform: translateY(-100px) scale(0.5); opacity: 0; }
  20% { transform: translateY(0) scale(1); opacity: 1; }
  80% { transform: translateY(0) scale(1); opacity: 1; }
  100% { transform: translateY(150px) scale(0.8); opacity: 0; }
}
</style>