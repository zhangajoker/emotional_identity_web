<template>
  <section class="recovery-shell">
    <div class="recovery-card">
      <div class="recovery-icon">↺</div>
      <p class="eyebrow">密码找回</p>
      <h1>设置一个新密码</h1>

      <p v-if="!token" class="state-message error">
        重置链接缺少令牌，请重新申请密码找回。
      </p>

      <template v-else>
        <p class="description">新密码至少 8 个字符。保存后，旧登录会话会全部失效。</p>

        <form class="recovery-form" @submit.prevent="submit">
          <label>
            <span>新密码</span>
            <el-input
              v-model="password"
              type="password"
              show-password
              maxlength="128"
              autocomplete="new-password"
            />
          </label>

          <label>
            <span>确认新密码</span>
            <el-input
              v-model="confirmPassword"
              type="password"
              show-password
              maxlength="128"
              autocomplete="new-password"
            />
          </label>

          <p v-if="errorMessage" class="state-message error">
            {{ errorMessage }}
          </p>

          <p v-if="successMessage" class="state-message success">
            {{ successMessage }}
          </p>

          <el-button
            v-if="!successMessage"
            native-type="submit"
            class="primary-button"
            :loading="submitting"
          >
            保存新密码
          </el-button>

          <el-button
            v-else
            class="primary-button"
            @click="returnToLogin"
          >
            返回登录
          </el-button>
        </form>
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api/client'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const password = ref('')
const confirmPassword = ref('')
const submitting = ref(false)
const successMessage = ref('')
const errorMessage = ref('')

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
  return '密码重置失败，请稍后重试'
}

async function submit() {
  errorMessage.value = ''

  if (password.value.length < 8) {
    errorMessage.value = '密码至少需要 8 个字符'
    return
  }

  if (password.value !== confirmPassword.value) {
    errorMessage.value = '两次输入的密码不一致'
    return
  }

  submitting.value = true

  try {
    const response = await api.post('/auth/password/reset', {
      token: token.value,
      new_password: password.value,
    })
    successMessage.value = response.data.message
    await authStore.logout()
  } catch (error) {
    errorMessage.value = getErrorDetail(error)
  } finally {
    submitting.value = false
  }
}

async function returnToLogin() {
  await router.push('/')
}
</script>

<style scoped>
.recovery-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 28px 16px;
  box-sizing: border-box;
}

.recovery-card {
  width: min(450px, 100%);
  padding: 34px;
  box-sizing: border-box;
  text-align: center;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(255, 255, 255, 0.9);
  border-radius: 28px;
  box-shadow: 0 24px 58px rgba(125, 90, 80, 0.12);
  backdrop-filter: blur(20px);
}

.recovery-icon {
  width: 64px;
  height: 64px;
  display: grid;
  place-items: center;
  margin: 0 auto 16px;
  border-radius: 21px;
  color: #6d4c41;
  background: linear-gradient(135deg, #ffd7dc, #d6f1e7);
  font-size: 30px;
}

.eyebrow {
  margin: 0 0 7px;
  color: #b07f8a;
  font-size: 12px;
  letter-spacing: 0.16em;
}

h1 {
  margin: 0 0 12px;
  color: #5d4037;
  font-size: 26px;
}

.description {
  margin: 0;
  color: #8d746a;
  line-height: 1.7;
  font-size: 14px;
}

.recovery-form {
  display: grid;
  gap: 16px;
  margin-top: 23px;
  text-align: left;
}

label {
  display: grid;
  gap: 7px;
  color: #6d4c41;
  font-size: 14px;
}

:deep(.el-input__wrapper) {
  min-height: 44px;
  border-radius: 13px;
  background: #fffaf8;
  box-shadow: 0 0 0 1px #f0ded8 inset;
}

.primary-button {
  width: 100%;
  min-height: 44px;
  border: 0;
  border-radius: 13px;
  color: #5d4037;
  background: linear-gradient(135deg, #f8bbc9, #ccebdc);
  font-weight: 700;
}

.state-message {
  margin: 0;
  padding: 10px 12px;
  border-radius: 10px;
  text-align: left;
  line-height: 1.6;
  font-size: 13px;
}

.state-message.error {
  color: #b42318;
  background: #fff1f0;
}

.state-message.success {
  color: #2f6d56;
  background: #edf9f3;
}

@media (max-width: 520px) {
  .recovery-card {
    padding: 27px 20px;
  }
}
</style>
