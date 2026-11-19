<template>
  <section class="verify-shell">
    <div class="verify-card">
      <div class="verify-icon">
        {{ status === 'success' ? '✓' : status === 'error' ? '!' : '…' }}
      </div>
      <h1>邮箱验证</h1>
      <p :class="['state-message', status]">
        {{ message }}
      </p>

      <el-button
        v-if="status !== 'loading'"
        class="primary-button"
        @click="goHome"
      >
        返回网站
      </el-button>
    </div>
  </section>
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api/client'

const route = useRoute()
const router = useRouter()

const status = ref<'loading' | 'success' | 'error'>('loading')
const message = ref('正在验证邮箱，请稍候...')

const token = computed(() => {
  const value = route.query.token
  return Array.isArray(value) ? value[0] || '' : value || ''
})

function getErrorDetail(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') {
      return detail
    }
  }
  return '邮箱验证失败'
}

async function verify() {
  if (!token.value) {
    status.value = 'error'
    message.value = '验证链接缺少令牌，请重新发送验证邮件。'
    return
  }

  try {
    const response = await api.post('/auth/email/verify', {
      token: token.value,
    })
    status.value = 'success'
    message.value = response.data.message
  } catch (error) {
    status.value = 'error'
    message.value = getErrorDetail(error)
  }
}

function goHome() {
  router.push('/settings')
}

onMounted(verify)
</script>

<style scoped>
.verify-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 28px 16px;
  box-sizing: border-box;
}

.verify-card {
  width: min(430px, 100%);
  padding: 36px;
  box-sizing: border-box;
  text-align: center;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(255, 255, 255, 0.9);
  border-radius: 28px;
  box-shadow: 0 24px 58px rgba(125, 90, 80, 0.12);
  backdrop-filter: blur(20px);
}

.verify-icon {
  width: 64px;
  height: 64px;
  display: grid;
  place-items: center;
  margin: 0 auto 18px;
  border-radius: 21px;
  color: #5d4037;
  background: linear-gradient(135deg, #ffd7dc, #d6f1e7);
  font-size: 30px;
  font-weight: 700;
}

h1 {
  margin: 0 0 18px;
  color: #5d4037;
  font-size: 26px;
}

.state-message {
  margin: 0 auto 22px;
  padding: 12px 14px;
  max-width: 360px;
  border-radius: 12px;
  line-height: 1.7;
  font-size: 14px;
}

.state-message.loading {
  color: #8d746a;
  background: #fff8f5;
}

.state-message.success {
  color: #2f6d56;
  background: #edf9f3;
}

.state-message.error {
  color: #b42318;
  background: #fff1f0;
}

.primary-button {
  min-width: 150px;
  border: 0;
  border-radius: 13px;
  color: #5d4037;
  background: linear-gradient(135deg, #f8bbc9, #ccebdc);
  font-weight: 700;
}
</style>
