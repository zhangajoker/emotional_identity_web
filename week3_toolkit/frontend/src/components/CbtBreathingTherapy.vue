<template>
  <div class="therapy-center-card">
    <div class="therapy-intro">
      <h3>🧘 4-7-8 科学心流呼吸法</h3>
      <p>跟随中央光圈的律动：吸气4秒 -> 屏息7秒 -> 呼气8秒。释放所有底层神经负荷。</p>
    </div>

    <div class="stage-core">
      <div class="circle-halo" :class="phaseClass">
        <div class="inner-core">
          <span class="action-hint">{{ phaseText }}</span>
          <span class="timer-countdown">{{ countdown }}s</span>
        </div>
      </div>
    </div>

    <div class="action-footer">
      <el-button type="primary" size="large" @click="toggleTherapy" class="action-btn">
        {{ running ? '结束静心' : '开启轻盈之旅' }}
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount } from 'vue'

const running = ref(false)
const phaseText = ref('准备')
const phaseClass = ref('idle')
const countdown = ref(0)

let mainTimer: number | null = null

const runBreathingCycle = () => {
  if (!running.value) return

  // Phase 1: 吸气 (4秒)
  phaseText.value = '📥 吸气...'
  phaseClass.value = 'inhale'
  countdown.value = 4

  let p1 = setInterval(() => {
    countdown.value--
    if(countdown.value <= 0) {
      clearInterval(p1)
      // Phase 2: 屏息 (7秒)
      phaseText.value = '🛑 屏息...'
      phaseClass.value = 'hold'
      countdown.value = 7
      let p2 = setInterval(() => {
        countdown.value--
        if(countdown.value <= 0) {
          clearInterval(p2)
          // Phase 3: 呼气 (8秒)
          phaseText.value = '💨 呼气...'
          phaseClass.value = 'exhale'
          countdown.value = 8
          let p3 = setInterval(() => {
            countdown.value--
            if(countdown.value <= 0) {
              clearInterval(p3)
              // 循环往复
              runBreathingCycle()
            }
          }, 1000)
        }
      }, 1000)
    }
  }, 1000)
}

const toggleTherapy = () => {
  running.value = !running.value
  if (running.value) {
    runBreathingCycle()
  } else {
    if (mainTimer) clearInterval(mainTimer)
    phaseText.value = '准备'
    phaseClass.value = 'idle'
    countdown.value = 0
  }
}

onBeforeUnmount(() => { if (mainTimer) clearInterval(mainTimer) })
</script>

<style scoped>
.therapy-center-card {
  background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(20px);
  border-radius: 32px; padding: 40px; text-align: center; max-width: 600px; margin: 0 auto;
}
.therapy-intro h3 { font-size: 1.5rem; color: #1e293b; margin-bottom: 10px; }
.therapy-intro p { color: #64748b; font-size: 0.9rem; line-height: 1.6; }
.stage-core { height: 350px; display: flex; justify-content: center; align-items: center; }

/* 核心呼吸缩放光圈动画 */
.circle-halo {
  width: 180px; height: 180px; border-radius: 50%;
  background: rgba(168, 230, 207, 0.2); display: flex; justify-content: center; align-items: center;
  transition: all 4s linear; box-shadow: 0 0 50px rgba(168, 230, 207, 0.1);
}
.inner-core {
  width: 130px; height: 130px; border-radius: 50%; background: #ffffff;
  display: flex; flex-direction: column; justify-content: center; align-items: center;
  box-shadow: 0 10px 30px rgba(0,0,0,0.04);
}
.action-hint { font-size: 1.1rem; font-weight: bold; color: #334155; }
.timer-countdown { font-size: 1.3rem; color: #94a3b8; margin-top: 5px; }

/* 状态样式控制 */
.inhale { transform: scale(1.6); background: rgba(168, 230, 207, 0.5); transition: all 4s ease-out; }
.hold { transform: scale(1.6); background: rgba(255, 213, 79, 0.4); transition: all 7s linear; }
.exhale { transform: scale(1.0); background: rgba(144, 202, 249, 0.4); transition: all 8s ease-in; }

.action-btn { background: #1e293b; border: none; padding: 12px 35px; border-radius: 20px; }
</style>