<template>
  <section class="profile-view">
    <div v-if="loading" class="profile-state">
      正在进入个人空间...
    </div>

    <div v-else-if="errorMessage" class="profile-state error">
      {{ errorMessage }}
    </div>

    <template v-else-if="profile">
      <header class="profile-hero">
        <div class="profile-avatar">
          <img
            v-if="profile.avatar_url"
            :src="profile.avatar_url"
            :alt="`${profile.display_name}的头像`"
          />
          <span v-else>{{ avatarText }}</span>
        </div>

        <div class="profile-identity">
          <p class="eyebrow">{{ isOwnProfile ? '我的空间' : '成员主页' }}</p>
          <h1>{{ profile.display_name }}</h1>
          <p class="username">@{{ profile.username }}</p>
          <p class="bio">
            {{ profile.bio || '这个人还在慢慢写下自己的介绍。' }}
          </p>

          <div class="profile-stats">
            <span>
              <strong>{{ profile.post_count }}</strong>
              动态
            </span>
            <span v-if="isOwnProfile" class="privacy-hint">
              自己的私密动态也会显示在这里
            </span>
          </div>
        </div>

        <div class="profile-actions">
          <button
            v-if="isOwnProfile"
            type="button"
            class="secondary-button"
            @click="startEditing"
          >
            编辑资料
          </button>
          <button
            type="button"
            class="primary-button"
            @click="goToComposer"
          >
            发布动态
          </button>
        </div>
      </header>

      <section v-if="editing" class="edit-card">
        <div class="edit-heading">
          <div>
            <p class="eyebrow">个人资料</p>
            <h2>让别人更了解你</h2>
          </div>
          <button
            type="button"
            class="close-edit"
            @click="editing = false"
          >
            取消
          </button>
        </div>

        <label>
          <span>显示名称</span>
          <el-input
            v-model="draftDisplayName"
            maxlength="64"
          />
        </label>

        <label>
          <span>个人简介</span>
          <el-input
            v-model="draftBio"
            type="textarea"
            :rows="4"
            maxlength="500"
            show-word-limit
            resize="none"
          />
        </label>

        <el-button
          class="save-profile"
          :loading="saving"
          :disabled="!draftDisplayName.trim()"
          @click="saveProfile"
        >
          保存资料
        </el-button>
      </section>

      <div class="timeline-heading">
        <div>
          <p class="eyebrow">动态</p>
          <h2>
            {{ isOwnProfile ? '我的心情足迹' : `${profile.display_name}的心情足迹` }}
          </h2>
        </div>
        <span>
          {{ isOwnProfile ? '公开与私密' : '仅公开动态' }}
        </span>
      </div>

      <div v-if="postsLoading" class="profile-state compact">
        正在读取动态...
      </div>

      <div v-else-if="posts.length === 0" class="profile-state compact">
        {{ isOwnProfile ? '还没有动态，记录一次此刻的心情吧。' : '这里暂时没有公开动态。' }}
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
        v-if="nextCursor"
        type="button"
        class="load-more"
        :disabled="loadingMore"
        @click="loadMorePosts"
      >
        {{ loadingMore ? '正在加载...' : '加载更早的动态' }}
      </button>
    </template>
  </section>
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import SocialPostCard from '../components/SocialPostCard.vue'
import {
  fetchProfile,
  fetchUserPosts,
  updateMyProfile,
  type SocialPost,
  type SocialProfile,
} from '../api/social'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const profile = ref<SocialProfile | null>(null)
const posts = ref<SocialPost[]>([])
const loading = ref(true)
const postsLoading = ref(true)
const loadingMore = ref(false)
const errorMessage = ref('')
const nextCursor = ref<number | null>(null)
const editing = ref(false)
const saving = ref(false)
const draftDisplayName = ref('')
const draftBio = ref('')

const userId = computed(() => Number(route.params.userId))
const isOwnProfile = computed(
  () => authStore.user?.id === userId.value,
)
const avatarText = computed(
  () => profile.value?.display_name.trim().slice(0, 1) || '✦',
)

function getErrorDetail(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') {
      return detail
    }
  }
  return '读取个人空间失败'
}

async function loadProfile() {
  if (!Number.isInteger(userId.value) || userId.value <= 0) {
    errorMessage.value = '用户编号无效'
    loading.value = false
    return
  }

  loading.value = true
  postsLoading.value = true
  errorMessage.value = ''
  posts.value = []
  nextCursor.value = null
  editing.value = false

  try {
    profile.value = await fetchProfile(userId.value)
    const result = await fetchUserPosts(userId.value)
    posts.value = result.data
    nextCursor.value = result.next_cursor
  } catch (error) {
    profile.value = null
    errorMessage.value = getErrorDetail(error)
  } finally {
    loading.value = false
    postsLoading.value = false
  }
}

function startEditing() {
  if (!profile.value) {
    return
  }

  draftDisplayName.value = profile.value.display_name
  draftBio.value = profile.value.bio
  editing.value = true
}

async function saveProfile() {
  const displayName = draftDisplayName.value.trim()

  if (!displayName) {
    ElMessage.error('显示名称不能为空')
    return
  }

  saving.value = true

  try {
    profile.value = await updateMyProfile({
      display_name: displayName,
      bio: draftBio.value.trim(),
    })
    authStore.updateUser({
      display_name: profile.value.display_name,
    })
    posts.value = posts.value.map((post) => ({
      ...post,
      display_name: profile.value!.display_name,
    }))
    editing.value = false
    ElMessage.success('个人资料已更新')
  } catch (error) {
    ElMessage.error(getErrorDetail(error))
  } finally {
    saving.value = false
  }
}

async function loadMorePosts() {
  if (!nextCursor.value || loadingMore.value) {
    return
  }

  loadingMore.value = true

  try {
    const result = await fetchUserPosts(
      userId.value,
      nextCursor.value,
    )
    posts.value.push(...result.data)
    nextCursor.value = result.next_cursor
  } catch (error) {
    ElMessage.error(getErrorDetail(error))
  } finally {
    loadingMore.value = false
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

  if (profile.value) {
    profile.value.post_count = Math.max(
      0,
      profile.value.post_count - 1,
    )
  }
}

function goToComposer() {
  router.push('/space')
}

watch(
  () => route.params.userId,
  loadProfile,
  { immediate: true },
)
</script>

<style scoped>
.profile-view {
  width: min(760px, 100%);
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.profile-hero {
  display: flex;
  align-items: center;
  gap: 21px;
  padding: 29px;
  border: 1px solid rgba(255, 255, 255, 0.9);
  border-radius: 28px;
  background:
    radial-gradient(circle at 92% 6%, rgba(214, 241, 231, 0.78), transparent 36%),
    linear-gradient(135deg, rgba(255, 242, 238, 0.9), rgba(255, 255, 255, 0.76));
  box-shadow: 0 20px 48px rgba(120, 90, 80, 0.09);
}

.profile-avatar {
  flex: 0 0 92px;
  width: 92px;
  height: 92px;
  display: grid;
  place-items: center;
  overflow: hidden;
  border-radius: 30px;
  color: #6d4c41;
  background: linear-gradient(135deg, #ffd7dc, #d6f1e7);
  font-size: 36px;
  font-weight: 700;
}

.profile-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.profile-identity {
  flex: 1;
  min-width: 0;
}

.eyebrow {
  margin: 0 0 5px;
  color: #b07f8a;
  font-size: 11px;
  letter-spacing: 0.14em;
}

.profile-identity h1 {
  margin: 0;
  color: #5d4037;
  font-size: clamp(25px, 4vw, 34px);
}

.username {
  margin: 4px 0 10px;
  color: #a1887f;
  font-size: 12px;
}

.bio {
  margin: 0;
  color: #79645b;
  line-height: 1.7;
  white-space: pre-wrap;
  font-size: 14px;
}

.profile-stats {
  display: flex;
  align-items: center;
  gap: 13px;
  flex-wrap: wrap;
  margin-top: 14px;
  color: #9a8177;
  font-size: 12px;
}

.profile-stats strong {
  margin-right: 4px;
  color: #6d4c41;
  font-size: 17px;
}

.privacy-hint {
  padding: 4px 8px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.62);
}

.profile-actions {
  display: grid;
  gap: 8px;
}

.primary-button,
.secondary-button,
.save-profile {
  border: 0;
  border-radius: 12px;
  padding: 9px 14px;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 700;
}

.primary-button,
.save-profile {
  color: #5d4037;
  background: linear-gradient(135deg, #f8bbc9, #ccebdc);
}

.secondary-button {
  color: #755b52;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid #eadbd5;
}

.edit-card {
  display: grid;
  gap: 15px;
  padding: 24px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.76);
  box-shadow: 0 14px 34px rgba(120, 90, 80, 0.06);
}

.edit-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.edit-heading h2,
.timeline-heading h2 {
  margin: 0;
  color: #5d4037;
  font-size: 21px;
}

.close-edit {
  border: 0;
  background: transparent;
  color: #9a7a70;
  cursor: pointer;
}

.edit-card label {
  display: grid;
  gap: 7px;
  color: #6d4c41;
  font-size: 13px;
}

:deep(.el-input__wrapper),
:deep(.el-textarea__inner) {
  border-radius: 13px;
  background: #fffaf8;
  box-shadow: 0 0 0 1px #f0ded8 inset;
}

.save-profile {
  justify-self: start;
  min-width: 120px;
}

.timeline-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
}

.timeline-heading > span {
  color: #a1887f;
  font-size: 12px;
}

.profile-state {
  padding: 70px 20px;
  border-radius: 22px;
  text-align: center;
  color: #a1887f;
  background: rgba(255, 255, 255, 0.58);
}

.profile-state.compact {
  padding: 34px 20px;
}

.profile-state.error {
  color: #b42318;
  background: #fff1f0;
}

.post-list {
  display: grid;
  gap: 15px;
}

.load-more {
  align-self: center;
  border: 1px solid rgba(141, 110, 99, 0.16);
  border-radius: 11px;
  padding: 9px 18px;
  color: #7c6259;
  background: rgba(255, 255, 255, 0.68);
  cursor: pointer;
}

@media (max-width: 640px) {
  .profile-hero {
    align-items: flex-start;
    flex-wrap: wrap;
    padding: 22px 18px;
  }

  .profile-avatar {
    flex-basis: 70px;
    width: 70px;
    height: 70px;
    border-radius: 23px;
    font-size: 28px;
  }

  .profile-actions {
    width: 100%;
    grid-template-columns: 1fr 1fr;
  }

  .edit-card {
    padding: 19px;
  }
}
</style>
