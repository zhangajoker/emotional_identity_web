<template>
  <FloatingBackground />

  <div v-if="authStore.loading" class="session-loading">
    <div class="loading-card">正在确认登录状态...</div>
  </div>

  <RouterView v-else-if="isPublicAuthRoute" />

  <AuthPanel v-else-if="!authStore.user" />

  <div v-else class="app-container">
    <div class="session-bar">
      <span>你好，{{ authStore.user.display_name }}</span>
      <RouterLink
        :to="`/u/${authStore.user.id}`"
        class="settings-link"
      >
        我的主页
      </RouterLink>
      <RouterLink to="/settings" class="settings-link">
        账号设置
      </RouterLink>
      <el-button text class="logout-button" @click="handleLogout">
        退出登录
      </el-button>
    </div>

    <header class="header">
      <h1>✦ 情绪感知日记</h1>
      <p class="subtitle">无论是哪种心情，都值得被温柔以待</p>
    </header>

    <main class="main-content">
      <nav class="main-nav" aria-label="主要导航">
        <RouterLink to="/" class="nav-link">
          <span>◉</span>
          情绪感知
        </RouterLink>
        <RouterLink to="/timeline" class="nav-link">
          <span>◷</span>
          时光长廊
        </RouterLink>
        <RouterLink to="/therapy" class="nav-link">
          <span>♨</span>
          呼吸疗愈
        </RouterLink>
        <RouterLink to="/space" class="nav-link">
          <span>✦</span>
          情绪空间
        </RouterLink>
        <RouterLink to="/chat" class="nav-link">
          <span>◌</span>
          情感陪伴
        </RouterLink>
      </nav>

      <RouterView v-slot="{ Component }">
        <Transition name="view-fade" mode="out-in">
          <div :key="$route.fullPath" class="view-section">
            <component :is="Component" />
          </div>
        </Transition>
      </RouterView>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import {
  RouterLink,
  RouterView,
  useRoute,
  useRouter,
} from 'vue-router'
import AuthPanel from './components/AuthPanel.vue'
import FloatingBackground from './components/FloatingBackground.vue'
import { useAuthStore } from './stores/auth'
import { useMoodStore } from './stores/mood'

const authStore = useAuthStore()
const moodStore = useMoodStore()
const router = useRouter()
const route = useRoute()

const isPublicAuthRoute = computed(
  () =>
    route.name === 'reset-password' ||
    route.name === 'verify-email',
)

onMounted(() => {
  authStore.restoreSession()
})

async function handleLogout() {
  moodStore.resetEmotion()
  await authStore.logout()
  await router.push('/')
}
</script>

<style scoped>
.session-loading {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  box-sizing: border-box;
}

.loading-card {
  padding: 18px 28px;
  border-radius: 18px;
  color: var(--text-main);
  background: rgba(255, 255, 255, 0.75);
  box-shadow: 0 16px 40px rgba(120, 90, 80, 0.1);
  backdrop-filter: blur(16px);
}

.app-container {
  width: min(1040px, 100%);
  max-width: 100%;
  min-width: 0;
  min-height: 100vh;
  margin: 0 auto;
  padding: 28px 20px 48px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  z-index: 1;
}

.session-bar {
  width: 100%;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 10px;
  color: var(--text-light);
  font-size: 14px;
}

.settings-link {
  padding: 6px 10px;
  border-radius: 10px;
  color: var(--text-main);
  text-decoration: none;
  background: rgba(255, 255, 255, 0.5);
  white-space: nowrap;
}

.logout-button {
  color: var(--text-main) !important;
  border: 1px solid rgba(130, 100, 90, 0.16) !important;
  border-radius: 12px;
}

.header {
  margin: 16px 0 30px;
  text-align: center;
}

.header h1 {
  margin: 0 0 10px;
  color: var(--text-main);
  font-size: clamp(30px, 5vw, 42px);
}

.subtitle {
  margin: 0;
  color: var(--text-light);
  font-size: 1.05rem;
}

.main-content {
  width: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.main-nav {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  display: flex;
  justify-content: center;
  gap: 8px;
}

.nav-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-width: 112px;
  padding: 11px 15px;
  border: 1px solid rgba(255, 255, 255, 0.9);
  border-radius: 14px;
  color: #8d6e63;
  text-decoration: none;
  background: rgba(255, 255, 255, 0.58);
  box-shadow: 0 7px 18px rgba(130, 100, 90, 0.05);
  transition:
    transform 0.2s ease,
    color 0.2s ease,
    background 0.2s ease;
}

.nav-link:hover {
  color: #5d4037;
  transform: translateY(-2px);
}

.nav-link.router-link-active {
  color: #5d4037;
  background: #ffffff;
  border-color: rgba(248, 187, 208, 0.75);
  box-shadow: 0 10px 24px rgba(180, 120, 130, 0.12);
}

.view-section {
  width: 100%;
}

.view-fade-enter-active,
.view-fade-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}

.view-fade-enter-from,
.view-fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

@media (max-width: 760px) {
  .app-container {
    padding: 20px 12px 36px;
  }

  .header {
    margin: 20px 0 24px;
  }

  .session-bar {
    flex-wrap: wrap;
    justify-content: flex-end;
    row-gap: 6px;
  }

  .session-bar > span {
    margin-right: auto;
  }

  .header h1 {
    font-size: 27px;
  }

  .subtitle {
    font-size: 14px;
  }

  .main-nav {
    justify-content: flex-start;
    overflow-x: auto;
    overflow-y: hidden;
    overscroll-behavior-x: contain;
    -webkit-overflow-scrolling: touch;
    scroll-snap-type: x proximity;
    padding: 4px 2px 10px;
    box-sizing: border-box;
    scrollbar-width: none;
  }

  .main-nav::-webkit-scrollbar {
    display: none;
  }

  .nav-link {
    min-width: max-content;
    padding: 10px 13px;
    flex: 0 0 auto;
    font-size: 14px;
    scroll-snap-align: start;
  }
}
</style>
