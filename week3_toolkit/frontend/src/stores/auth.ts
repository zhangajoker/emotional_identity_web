import axios from 'axios'
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'

export interface AuthUser {
  id: number
  username: string
  display_name: string
}

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail

    if (typeof detail === 'string') {
      return detail
    }

    if (Array.isArray(detail) && detail.length > 0) {
      const message = detail
        .map((item) =>
          typeof item?.msg === 'string' ? item.msg : '',
        )
        .find(Boolean)

      if (message) {
        return `输入信息不符合要求：${message}`
      }
    }

    if (!error.response) {
      return '无法连接服务器，请检查网络和后端服务'
    }
  }

  return '请求失败，请检查输入后重试'
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const loading = ref(true)
  const submitting = ref(false)
  const error = ref('')

  async function restoreSession() {
    loading.value = true

    try {
      const response = await api.get('/auth/me')
      user.value = response.data.user
    } catch {
      user.value = null
    } finally {
      loading.value = false
    }
  }

  async function login(username: string, password: string) {
    submitting.value = true
    error.value = ''

    try {
      const response = await api.post('/auth/login', {
        username,
        password,
      })

      user.value = response.data.user
      return true
    } catch (requestError) {
      error.value = getErrorMessage(requestError)
      return false
    } finally {
      submitting.value = false
    }
  }

  async function register(
    username: string,
    displayName: string,
    password: string,
  ) {
    submitting.value = true
    error.value = ''

    try {
      const response = await api.post('/auth/register', {
        username,
        display_name: displayName,
        password,
      })

      user.value = response.data.user
      return true
    } catch (requestError) {
      error.value = getErrorMessage(requestError)
      return false
    } finally {
      submitting.value = false
    }
  }

  async function logout() {
    try {
      await api.post('/auth/logout')
    } finally {
      user.value = null
      error.value = ''
    }
  }

  function clearError() {
    error.value = ''
  }

  function updateUser(patch: Partial<AuthUser>) {
    if (user.value) {
      user.value = {
        ...user.value,
        ...patch,
      }
    }
  }

  return {
    user,
    loading,
    submitting,
    error,
    restoreSession,
    login,
    register,
    logout,
    clearError,
    updateUser,
  }
})
