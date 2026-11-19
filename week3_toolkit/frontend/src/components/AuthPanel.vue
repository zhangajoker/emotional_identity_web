<template>
  <section class="auth-shell">
    <div class="auth-card">
      <div class="auth-brand">
        <span class="auth-logo">✦</span>
        <div>
          <h1>情绪感知空间</h1>
          <p>先找到你，再温柔地记录心情</p>
        </div>
      </div>

      <button
        v-if="mode === 'forgot'"
        type="button"
        class="back-button"
        @click="switchMode('login')"
      >
        ← 返回登录
      </button>

      <div v-else class="mode-switch" role="tablist">
        <button
          type="button"
          :class="{ active: mode === 'login' }"
          @click="switchMode('login')"
        >
          登录
        </button>
        <button
          type="button"
          :class="{ active: mode === 'register' }"
          @click="switchMode('register')"
        >
          注册
        </button>
      </div>

      <form
        v-if="mode === 'forgot'"
        class="auth-form"
        @submit.prevent="submit"
      >
        <div class="forgot-heading">
          <h2>找回密码</h2>
          <p>输入已绑定并验证的邮箱，我们会发送一次性重置链接。</p>
        </div>

        <label class="form-field">
          <span>绑定邮箱</span>
          <el-input
            v-model="recoveryEmail"
            type="email"
            maxlength="254"
            placeholder="name@example.com"
            autocomplete="email"
          />
        </label>

        <p v-if="recoverySent" class="recovery-success">
          如果该邮箱已绑定账号，重置邮件会很快发送。请检查收件箱和垃圾邮件。
        </p>

        <p v-if="localError || authStore.error" class="form-error">
          {{ localError || authStore.error }}
        </p>

        <el-button
          native-type="submit"
          class="submit-button"
          :loading="recoverySubmitting"
        >
          发送重置邮件
        </el-button>
      </form>

      <form v-else class="auth-form" @submit.prevent="submit">
        <label v-if="mode === 'register'" class="form-field">
          <span>显示名称</span>
          <el-input
            v-model="displayName"
            maxlength="64"
            placeholder="别人会看到的名字"
            autocomplete="nickname"
          />
        </label>

        <label class="form-field">
          <span>用户名</span>
          <el-input
            v-model="username"
            maxlength="32"
            placeholder="字母、数字、中文或下划线"
            autocomplete="username"
          />
        </label>

        <label class="form-field">
          <span>密码</span>
          <el-input
            v-model="password"
            type="password"
            show-password
            maxlength="128"
            placeholder="至少 8 个字符"
            :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
          />
        </label>

        <label v-if="mode === 'register'" class="form-field">
          <span>确认密码</span>
          <el-input
            v-model="confirmPassword"
            type="password"
            show-password
            maxlength="128"
            placeholder="再次输入密码"
            autocomplete="new-password"
          />
        </label>

        <p v-if="localError || authStore.error" class="form-error">
          {{ localError || authStore.error }}
        </p>

        <el-button
          native-type="submit"
          class="submit-button"
          :loading="authStore.submitting"
        >
          {{ mode === 'login' ? '进入我的空间' : '创建账号并进入' }}
        </el-button>

        <button
          v-if="mode === 'login'"
          type="button"
          class="forgot-link"
          @click="switchMode('forgot')"
        >
          忘记密码？
        </button>
      </form>

      <p class="privacy-note">
        你的心情日记默认仅自己可见。请妥善保管账号密码。
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api/client'
import { useAuthStore } from '../stores/auth'

type AuthMode = 'login' | 'register' | 'forgot'

const authStore = useAuthStore()

const mode = ref<AuthMode>('login')
const username = ref('')
const displayName = ref('')
const password = ref('')
const confirmPassword = ref('')
const recoveryEmail = ref('')
const localError = ref('')
const recoverySubmitting = ref(false)
const recoverySent = ref(false)

function switchMode(nextMode: AuthMode) {
  mode.value = nextMode
  localError.value = ''
  password.value = ''
  confirmPassword.value = ''
  recoverySent.value = false
  authStore.clearError()
}

async function submit() {
  localError.value = ''
  authStore.clearError()

  if (mode.value === 'forgot') {
    const email = recoveryEmail.value.trim()

    if (!email) {
      localError.value = '请输入绑定邮箱'
      return
    }

    recoverySubmitting.value = true

    try {
      const response = await api.post('/auth/password/forgot', {
        email,
      })
      recoverySent.value = true
      ElMessage.success(response.data.message)
    } catch {
      localError.value = '邮件请求失败，请稍后重试'
    } finally {
      recoverySubmitting.value = false
    }

    return
  }

  const normalizedUsername = username.value.trim()
  const normalizedDisplayName = displayName.value.trim()

  if (!normalizedUsername) {
    localError.value = '请输入用户名'
    return
  }

  if (mode.value === 'register') {
    if (normalizedUsername.length < 3) {
      localError.value = '用户名至少需要 3 个字符'
      return
    }

    if (!/^[\w\u4e00-\u9fff]+$/.test(normalizedUsername)) {
      localError.value = '用户名只能包含文字、字母、数字和下划线'
      return
    }
  }

  if (password.value.length < 8) {
    localError.value = '密码至少需要 8 个字符'
    return
  }

  if (mode.value === 'register') {
    if (!normalizedDisplayName) {
      localError.value = '请输入显示名称'
      return
    }

    if (password.value !== confirmPassword.value) {
      localError.value = '两次输入的密码不一致'
      return
    }
  }

  const succeeded =
    mode.value === 'login'
      ? await authStore.login(normalizedUsername, password.value)
      : await authStore.register(
          normalizedUsername,
          normalizedDisplayName,
          password.value,
        )

  if (succeeded) {
    ElMessage.success(
      mode.value === 'login' ? '欢迎回来' : '账号创建成功',
    )
    password.value = ''
    confirmPassword.value = ''
  }
}
</script>

<style scoped>
.auth-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px 18px;
  box-sizing: border-box;
}

.auth-card {
  width: min(440px, 100%);
  padding: 34px;
  box-sizing: border-box;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.9);
  border-radius: 30px;
  box-shadow: 0 24px 60px rgba(125, 90, 80, 0.12);
  backdrop-filter: blur(20px);
}

.auth-brand {
  display: flex;
  gap: 14px;
  align-items: center;
  margin-bottom: 26px;
}

.auth-logo {
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  border-radius: 18px;
  background: linear-gradient(135deg, #ffd7dc, #d6f1e7);
  color: #5d4037;
  font-size: 28px;
}

.auth-brand h1 {
  margin: 0 0 5px;
  font-size: 24px;
  color: #5d4037;
}

.auth-brand p {
  margin: 0;
  color: #9a8177;
  font-size: 14px;
}

.mode-switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  padding: 5px;
  margin-bottom: 24px;
  border-radius: 16px;
  background: rgba(248, 187, 208, 0.14);
}

.back-button {
  margin-bottom: 20px;
  border: 0;
  padding: 0;
  color: #9a7a70;
  background: transparent;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
}

.forgot-heading {
  margin-bottom: 3px;
}

.forgot-heading h2 {
  margin: 0 0 7px;
  color: #5d4037;
  font-size: 22px;
}

.forgot-heading p {
  margin: 0;
  color: #9a8177;
  line-height: 1.6;
  font-size: 13px;
}

.mode-switch button {
  border: 0;
  padding: 11px 16px;
  border-radius: 12px;
  color: #8d6e63;
  background: transparent;
  cursor: pointer;
  font: inherit;
  transition: all 0.25s ease;
}

.mode-switch button.active {
  color: #5d4037;
  background: #fff;
  box-shadow: 0 6px 18px rgba(140, 100, 90, 0.1);
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 17px;
}

.form-field {
  display: flex;
  flex-direction: column;
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

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #e6a9b5 inset;
}

.form-error {
  margin: 0;
  padding: 10px 12px;
  border-radius: 10px;
  color: #b42318;
  background: #fff1f0;
  font-size: 13px;
}

.submit-button {
  width: 100%;
  min-height: 46px;
  border: 0;
  border-radius: 15px;
  color: #5d4037;
  background: linear-gradient(135deg, #f8bbc9, #ccebdc);
  font-weight: 700;
  font-size: 15px;
}

.forgot-link {
  align-self: center;
  border: 0;
  padding: 2px 6px;
  color: #9a7a70;
  background: transparent;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
}

.recovery-success {
  margin: 0;
  padding: 11px 12px;
  border-radius: 10px;
  color: #2f6d56;
  background: #edf9f3;
  line-height: 1.6;
  font-size: 13px;
}

.privacy-note {
  margin: 20px 4px 0;
  text-align: center;
  color: #a1887f;
  line-height: 1.6;
  font-size: 12px;
}

@media (max-width: 480px) {
  .auth-shell {
    padding: 18px 12px;
  }

  .auth-card {
    padding: 26px 20px;
    border-radius: 24px;
  }

  .auth-brand h1 {
    font-size: 21px;
  }
}
</style>
