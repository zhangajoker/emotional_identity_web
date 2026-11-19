<template>
  <section class="settings-view">
    <div class="settings-card">
      <p class="eyebrow">账号安全</p>
      <h2>绑定找回邮箱</h2>
      <p class="description">
        邮箱验证成功后，忘记密码时可以通过一次性邮件重置密码。
        QQ 邮箱、163 邮箱等普通邮箱均可使用。
      </p>

      <div v-if="currentEmail" class="current-email">
        <span>当前邮箱</span>
        <strong>{{ currentEmail }}</strong>
        <em :class="{ verified: emailVerified }">
          {{ emailVerified ? '已验证' : '待验证' }}
        </em>
      </div>

      <form @submit.prevent="requestBinding">
        <label>
          <span>邮箱地址</span>
          <el-input
            v-model="email"
            type="email"
            maxlength="254"
            placeholder="name@qq.com"
            autocomplete="email"
          />
        </label>

        <p v-if="message" :class="['message', messageType]">
          {{ message }}
        </p>

        <el-button
          native-type="submit"
          class="primary-button"
          :loading="submitting"
          :disabled="!email.trim()"
        >
          发送验证邮件
        </el-button>
      </form>

      <div class="safety-note">
        <strong>安全说明</strong>
        <p>
          邮箱只有点击验证链接后才生效。重置链接仅可使用一次，
          修改密码后所有旧登录状态都会失效。
        </p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import axios from 'axios'
import { onMounted, ref } from 'vue'
import { api } from '../api/client'

const email = ref('')
const currentEmail = ref<string | null>(null)
const emailVerified = ref(false)
const submitting = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

function getErrorDetail(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') {
      return detail
    }
  }
  return '请求失败，请稍后重试'
}

async function loadEmail() {
  try {
    const response = await api.get('/auth/email/me')
    currentEmail.value = response.data.data.email
    emailVerified.value = response.data.data.verified
    email.value = currentEmail.value || ''
  } catch {
    message.value = '无法读取当前邮箱'
    messageType.value = 'error'
  }
}

async function requestBinding() {
  message.value = ''
  submitting.value = true

  try {
    const response = await api.post('/auth/email/request', {
      email: email.value.trim(),
    })
    message.value = response.data.message
    messageType.value = 'success'
  } catch (error) {
    message.value = getErrorDetail(error)
    messageType.value = 'error'
  } finally {
    submitting.value = false
  }
}

onMounted(loadEmail)
</script>

<style scoped>
.settings-view {
  width: min(720px, 100%);
  margin: 0 auto;
}

.settings-card {
  padding: 32px;
  border: 1px solid rgba(255, 255, 255, 0.9);
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 20px 48px rgba(120, 90, 80, 0.08);
  backdrop-filter: blur(20px);
}

.eyebrow {
  margin: 0 0 7px;
  color: #b07f8a;
  font-size: 12px;
  letter-spacing: 0.16em;
}

h2 {
  margin: 0 0 12px;
  color: #5d4037;
  font-size: 27px;
}

.description {
  margin: 0;
  color: #8d746a;
  line-height: 1.8;
  font-size: 14px;
}

.current-email {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin: 20px 0;
  padding: 13px 15px;
  border-radius: 14px;
  background: #fff8f5;
  color: #8d746a;
  font-size: 13px;
}

.current-email strong {
  color: #5d4037;
}

.current-email em {
  padding: 3px 8px;
  border-radius: 8px;
  color: #a35f43;
  background: #fff0e8;
  font-style: normal;
}

.current-email em.verified {
  color: #2f6d56;
  background: #e8f7ef;
}

form {
  display: grid;
  gap: 15px;
  margin-top: 22px;
}

label {
  display: grid;
  gap: 7px;
  color: #6d4c41;
  font-size: 14px;
}

:deep(.el-input__wrapper) {
  min-height: 45px;
  border-radius: 13px;
  background: #fffaf8;
  box-shadow: 0 0 0 1px #f0ded8 inset;
}

.primary-button {
  justify-self: start;
  min-width: 170px;
  border: 0;
  border-radius: 13px;
  color: #5d4037;
  background: linear-gradient(135deg, #f8bbc9, #ccebdc);
  font-weight: 700;
}

.message {
  margin: 0;
  padding: 11px 13px;
  border-radius: 11px;
  line-height: 1.6;
  font-size: 13px;
}

.message.success {
  color: #2f6d56;
  background: #edf9f3;
}

.message.error {
  color: #b42318;
  background: #fff1f0;
}

.safety-note {
  margin-top: 25px;
  padding: 15px 17px;
  border-radius: 14px;
  color: #8d746a;
  background: rgba(248, 187, 208, 0.1);
  line-height: 1.7;
  font-size: 13px;
}

.safety-note strong {
  color: #6d4c41;
}

.safety-note p {
  margin: 5px 0 0;
}

@media (max-width: 560px) {
  .settings-card {
    padding: 23px 18px;
  }

  h2 {
    font-size: 23px;
  }
}
</style>
