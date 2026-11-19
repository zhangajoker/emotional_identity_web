<template>
  <section class="social-view">
    <div class="social-hero">
      <div>
        <p class="eyebrow">情绪空间</p>
        <h2>把想说的话，轻轻放进这里</h2>
        <p class="hero-description">
          私密动态只有你自己能看到；公开动态仅对本站已登录成员可见。
        </p>
      </div>
      <span class="hero-symbol">✦</span>
    </div>

    <form class="composer" @submit.prevent="submitPost">
      <el-input
        v-model="draft"
        type="textarea"
        :rows="4"
        maxlength="2000"
        show-word-limit
        resize="none"
        placeholder="此刻发生了什么？你想留下怎样的心情？"
      />

      <div class="composer-options">
        <label>
          <span>心情</span>
          <select v-model="mood">
            <option value="">不标记</option>
            <option
              v-for="(meta, key) in moodStore.emotionDict"
              :key="key"
              :value="key"
            >
              {{ meta.emoji }} {{ meta.label }}
            </option>
          </select>
        </label>

        <label>
          <span>谁可以看</span>
          <select v-model="visibility">
            <option value="private">仅自己</option>
            <option value="public">所有登录成员</option>
          </select>
        </label>

        <el-button
          native-type="submit"
          class="publish-button"
          :loading="publishing"
          :disabled="!draft.trim()"
        >
          发布动态
        </el-button>
      </div>
    </form>

    <div class="feed-header">
      <div>
        <p class="eyebrow">动态流</p>
        <h3>最近的心情回声</h3>
      </div>
      <button type="button" class="refresh-button" @click="loadFeed()">
        刷新
      </button>
    </div>

    <div v-if="loading" class="feed-state">正在读取动态...</div>
    <div v-else-if="errorMessage" class="feed-state error">
      {{ errorMessage }}
    </div>
    <div v-else-if="posts.length === 0" class="feed-state">
      这里还很安静，发布第一条心情动态吧。
    </div>

    <div v-else class="post-list">
      <SocialPostCard
        v-for="post in posts"
        :key="post.id"
        :post="post"
        @update="updatePost"
        @remove="removePost"
      />
    </div>

    <button
      v-if="nextCursor && !loading"
      type="button"
      class="load-more"
      :disabled="loadingMore"
      @click="loadMore"
    >
      {{ loadingMore ? '正在加载...' : '加载更早的动态' }}
    </button>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import SocialPostCard from '../components/SocialPostCard.vue'
import {
  fetchFeed,
  publishPost,
  type SocialPost,
} from '../api/social'
import { useMoodStore } from '../stores/mood'

const moodStore = useMoodStore()

const posts = ref<SocialPost[]>([])
const draft = ref('')
const mood = ref('')
const visibility = ref<'private' | 'public'>('private')
const loading = ref(true)
const loadingMore = ref(false)
const publishing = ref(false)
const errorMessage = ref('')
const nextCursor = ref<number | null>(null)

function getErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') {
      return detail
    }
  }
  return '请求失败，请稍后重试'
}

async function loadFeed() {
  loading.value = true
  errorMessage.value = ''

  try {
    const result = await fetchFeed()
    posts.value = result.data
    nextCursor.value = result.next_cursor
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  if (!nextCursor.value || loadingMore.value) {
    return
  }

  loadingMore.value = true

  try {
    const result = await fetchFeed(nextCursor.value)
    posts.value.push(...result.data)
    nextCursor.value = result.next_cursor
  } catch (error) {
    ElMessage.error(getErrorMessage(error))
  } finally {
    loadingMore.value = false
  }
}

async function submitPost() {
  const content = draft.value.trim()

  if (!content) {
    return
  }

  publishing.value = true

  try {
    const post = await publishPost({
      content,
      mood: mood.value || null,
      visibility: visibility.value,
    })

    posts.value.unshift(post)
    draft.value = ''
    mood.value = ''
    ElMessage.success('动态已发布')
  } catch (error) {
    ElMessage.error(getErrorMessage(error))
  } finally {
    publishing.value = false
  }
}

function updatePost(updatedPost: SocialPost) {
  const index = posts.value.findIndex(
    (post) => post.id === updatedPost.id,
  )

  if (index !== -1) {
    posts.value[index] = updatedPost
  }
}

function removePost(postId: number) {
  posts.value = posts.value.filter((post) => post.id !== postId)
}

onMounted(loadFeed)
</script>

<style scoped>
.social-view {
  width: min(760px, 100%);
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.social-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 28px 30px;
  border: 1px solid rgba(255, 255, 255, 0.86);
  border-radius: 26px;
  background:
    radial-gradient(circle at 90% 15%, rgba(219, 246, 235, 0.82), transparent 34%),
    linear-gradient(135deg, rgba(255, 241, 238, 0.9), rgba(255, 255, 255, 0.78));
  box-shadow: 0 18px 42px rgba(120, 90, 80, 0.08);
}

.eyebrow {
  margin: 0 0 6px;
  color: #b07f8a;
  font-size: 12px;
  letter-spacing: 0.16em;
}

.social-hero h2 {
  margin: 0 0 9px;
  color: #5d4037;
  font-size: clamp(22px, 4vw, 29px);
}

.hero-description {
  margin: 0;
  max-width: 540px;
  color: #8d746a;
  line-height: 1.7;
  font-size: 14px;
}

.hero-symbol {
  flex: 0 0 auto;
  width: 72px;
  height: 72px;
  display: grid;
  place-items: center;
  border-radius: 24px;
  color: #6d4c41;
  background: rgba(255, 255, 255, 0.64);
  font-size: 34px;
}

.composer {
  padding: 22px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.76);
  box-shadow: 0 15px 35px rgba(120, 90, 80, 0.06);
}

:deep(.composer .el-textarea__inner) {
  border-radius: 16px;
  padding: 14px;
  background: #fffaf8;
  box-shadow: 0 0 0 1px #f0ded8 inset;
  color: #5d4840;
  line-height: 1.7;
}

.composer-options {
  display: flex;
  align-items: end;
  gap: 12px;
  margin-top: 14px;
}

.composer-options label {
  display: grid;
  gap: 5px;
  color: #9a8177;
  font-size: 12px;
}

.composer-options select {
  min-width: 145px;
  height: 38px;
  padding: 0 10px;
  border: 1px solid #eadbd5;
  border-radius: 11px;
  color: #6d4c41;
  background: #fff;
  outline: none;
}

.publish-button {
  margin-left: auto;
  height: 38px;
  border: 0;
  border-radius: 12px;
  color: #5d4037;
  background: linear-gradient(135deg, #f8bbc9, #ccebdc);
  font-weight: 700;
}

.feed-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
}

.feed-header h3 {
  margin: 0;
  color: #5d4037;
  font-size: 22px;
}

.refresh-button,
.load-more {
  border: 1px solid rgba(141, 110, 99, 0.16);
  border-radius: 11px;
  padding: 8px 13px;
  color: #7c6259;
  background: rgba(255, 255, 255, 0.68);
  cursor: pointer;
}

.feed-state {
  padding: 55px 20px;
  border-radius: 22px;
  text-align: center;
  color: #a1887f;
  background: rgba(255, 255, 255, 0.58);
}

.feed-state.error {
  color: #b42318;
  background: #fff1f0;
}

.post-list {
  display: grid;
  gap: 15px;
}

.load-more {
  align-self: center;
  padding: 10px 20px;
}

@media (max-width: 600px) {
  .social-hero {
    padding: 22px 18px;
  }

  .hero-symbol {
    display: none;
  }

  .composer {
    padding: 17px;
  }

  .composer-options {
    flex-wrap: wrap;
  }

  .composer-options label {
    flex: 1 1 130px;
  }

  .composer-options select {
    width: 100%;
    min-width: 0;
  }

  .publish-button {
    flex: 1 1 100%;
    margin-left: 0;
  }
}
</style>
