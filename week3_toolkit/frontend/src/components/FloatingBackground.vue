<template>
  <div class="floating-container">
    <img
      v-for="item in elements"
      :key="item.id"
      :src="item.src"
      class="floating-item"
      :style="item.style"
      alt="治愈背景元素"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

import boatImg from '../assets/boat.png'
import dogImg from '../assets/dog.png'
import balloonImg from '../assets/hot_air_balloon.png'
import kulomiImg from '../assets/kulomi.png'
import milkTeaImg from '../assets/milk_tea.png'

const images = [boatImg, dogImg, balloonImg, kulomiImg, milkTeaImg]

interface FloatingElement {
  id: number
  src: string
  style: Record<string, string>
}

const elements = ref<FloatingElement[]>([])

const generateElements = () => {
  const count = 25 // 设定飘落总数
  const tempElements: FloatingElement[] = []

  // 【核心修改 1：均匀分布逻辑】
  // 计算每个元素的“专属通道宽度” (例如 20个元素，每个占 5% 的屏幕宽度)
  const channelWidth = 100 / count

  for (let i = 0; i < count; i++) {
    const randomImg = images[Math.floor(Math.random() * images.length)]

    // 专属通道基准点 + 随机偏移 (允许在通道内左右波动，但不会越界跑到别人那里)
    const baseLeft = i * channelWidth
    const offset = (Math.random() - 0.5) * (channelWidth * 0.8)
    let left = baseLeft + (channelWidth / 2) + offset

    // 边界保护，防止图标溢出屏幕出现滚动条
    if (left < 2) left = 2
    if (left > 95) left = 95

    // 【核心修改 2：尺寸严格控制】
    // 限制尺寸在 24px - 42px 之间，保证小巧精致
    const sizePx = 50 + Math.random() * 18

    const duration = 15 + Math.random() * 25
    const delay = Math.random() * -30
    const rotateSpeed = Math.random() > 0.5 ? 1 : -1

    tempElements.push({
      id: i,
      src: randomImg,
      style: {
        left: `${left}vw`,
        width: `${sizePx}px`, // 直接写死具体的 px 宽度
        animationDuration: `${duration}s`,
        animationDelay: `${delay}s`,
        '--rotate-direction': rotateSpeed.toString()
      }
    })
  }
  elements.value = tempElements
}

onMounted(() => {
  generateElements()
})
</script>

<style scoped>
.floating-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.floating-item {
  position: absolute;
  top: -10%;
  opacity: 0.4;
  animation: floatDown linear infinite;
  filter: drop-shadow(0 4px 8px rgba(200, 150, 150, 0.2));
  object-fit: contain; /* 保证图片不变形 */
}

/* 优化后的轻盈摇曳动画 (去除了 scale 的干扰) */
@keyframes floatDown {
  0% {
    top: -10%;
    transform: translateX(0px) rotate(0deg);
    opacity: 0;
  }
  15% {
    opacity: 0.6;
  }
  50% {
    /* 缩小了横向摆动的幅度，看起来更温柔 */
    transform: translateX(30px) rotate(calc(45deg * var(--rotate-direction)));
  }
  85% {
    opacity: 0.6;
  }
  100% {
    top: 110%;
    transform: translateX(-15px) rotate(calc(90deg * var(--rotate-direction)));
    opacity: 0;
  }
}
</style>