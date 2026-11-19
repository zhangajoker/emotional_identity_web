<template>
  <article class="post-card">
    <header class="post-header">
      <div class="avatar">
        <img
          v-if="post.avatar_url"
          :src="post.avatar_url"
          :alt="`${post.display_name}的头像`"
        />
        <span v-else>{{ avatarText }}</span>
      </div>

      <div class="author-meta">
        <div class="author-line">
          <RouterLink
            :to="`/u/${post.user_id}`"
            class="author-link"
          >
            {{ post.display_name }}
          </RouterLink>
          <span class="username">@{{ post.username }}</span>
        </div>
        <div class="post-meta">
          <time>{{ formatTime(post.created_at) }}</time>
          <span class="visibility">
            {{ post.visibility === 'public' ? '公开' : '仅自己' }}
          </span>
        </div>
      </div>

      <button
        v-if="isOwner"
        type="button"
        class="delete-button"
        :disabled="deleting"
        @click="removePost"
      >
        删除
      </button>
    </header>

    <p class="post-content">{{ post.content }}</p>

    <div v-if="post.mood" class="mood-tag">
      <span>{{ moodMeta?.emoji || '◌' }}</span>
      {{ moodMeta?.label || post.mood }}
    </div>

    <footer class="post-actions">
      <button
        type="button"
        :class="{ active: post.liked_by_me }"
        :disabled="liking"
        @click="toggleLike"
      >
        <span>{{ post.liked_by_me ? '♥' : '♡' }}</span>
        喜欢 {{ post.reaction_count }}
      </button>

      <button
        type="button"
        :class="{ active: commentsOpen }"
        @click="toggleComments"
      >
        <span>◌</span>
        评论 {{ post.comment_count }}
      </button>
    </footer>

    <section v-if="commentsOpen" class="comments-panel">
      <div v-if="commentsLoading" class="comments-tip">
        正在读取评论...
      </div>

      <div v-else-if="comments.length === 0" class="comments-tip">
        还没有评论，写下第一句回应吧
      </div>

      <div v-else class="comment-list">
        <div
          v-for="comment in comments"
          :key="comment.id"
          class="comment-item"
        >
          <strong>{{ comment.display_name }}</strong>
          <p>{{ comment.content }}</p>
          <time>{{ formatTime(comment.created_at) }}</time>
        </div>
      </div>

      <form class="comment-form" @submit.prevent="submitComment">
        <el-input
          v-model="commentDraft"
          maxlength="1000"
          placeholder="写下你的回应..."
          :disabled="commenting"
        />
        <el-button
          native-type="submit"
          :loading="commenting"
          :disabled="!commentDraft.trim()"
        >
          发送
        </el-button>
      </form>
    </section>
  </article>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { RouterLink } from 'vue-router'
import {
  createComment,
  deletePost,
  fetchComments,
  likePost,
  unlikePost,
  type SocialComment,
  type SocialPost,
} from '../api/social'
import { useAuthStore } from '../stores/auth'
import { useMoodStore } from '../stores/mood'

const props = defineProps<{
  post: SocialPost
}>()

const emit = defineEmits<{
  update: [post: SocialPost]
  remove: [postId: number]
}>()

const authStore = useAuthStore()
const moodStore = useMoodStore()

const commentsOpen = ref(false)
const commentsLoading = ref(false)
const commentsLoaded = ref(false)
const comments = ref<SocialComment[]>([])
const commentDraft = ref('')
const commenting = ref(false)
const liking = ref(false)
const deleting = ref(false)

const isOwner = computed(
  () => authStore.user?.id === props.post.user_id,
)

const avatarText = computed(
  () => props.post.display_name.trim().slice(0, 1) || '✦',
)

const moodMeta = computed(() => {
  if (!props.post.mood) {
    return null
  }
  return moodStore.emotionDict[props.post.mood] || null
})

function normalizeDate(value: string) {
  if (/[zZ]$|[+-]\d{2}:\d{2}$/.test(value)) {
    return value
  }
  return `${value}Z`
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(normalizeDate(value)))
}

async function toggleLike() {
  liking.value = true

  try {
    const result = props.post.liked_by_me
      ? await unlikePost(props.post.id)
      : await likePost(props.post.id)

    emit('update', {
      ...props.post,
      liked_by_me: result.liked_by_me,
      reaction_count: result.reaction_count,
    })
  } catch {
    ElMessage.error('点赞操作失败')
  } finally {
    liking.value = false
  }
}

async function loadComments() {
  commentsLoading.value = true

  try {
    comments.value = await fetchComments(props.post.id)
    commentsLoaded.value = true
  } catch {
    ElMessage.error('读取评论失败')
  } finally {
    commentsLoading.value = false
  }
}

async function toggleComments() {
  commentsOpen.value = !commentsOpen.value

  if (commentsOpen.value && !commentsLoaded.value) {
    await loadComments()
  }
}

async function submitComment() {
  const content = commentDraft.value.trim()

  if (!content) {
    return
  }

  commenting.value = true

  try {
    const comment = await createComment(props.post.id, content)
    comments.value.push(comment)
    commentDraft.value = ''
    emit('update', {
      ...props.post,
      comment_count: props.post.comment_count + 1,
    })
  } catch {
    ElMessage.error('评论发送失败')
  } finally {
    commenting.value = false
  }
}

async function removePost() {
  try {
    await ElMessageBox.confirm(
      '删除后将从动态列表中移除，确定继续吗？',
      '删除动态',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
  } catch {
    return
  }

  deleting.value = true

  try {
    await deletePost(props.post.id)
    emit('remove', props.post.id)
    ElMessage.success('动态已删除')
  } catch {
    ElMessage.error('删除失败')
  } finally {
    deleting.value = false
  }
}
</script>

<style scoped>
.post-card {
  padding: 24px;
  border: 1px solid rgba(255, 255, 255, 0.86);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 16px 38px rgba(120, 90, 80, 0.07);
  backdrop-filter: blur(18px);
}

.post-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar {
  flex: 0 0 46px;
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  overflow: hidden;
  border-radius: 16px;
  color: #6d4c41;
  background: linear-gradient(135deg, #ffd7dc, #d6f1e7);
  font-size: 18px;
  font-weight: 700;
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.author-meta {
  flex: 1;
  min-width: 0;
}

.author-line {
  display: flex;
  align-items: baseline;
  gap: 7px;
  flex-wrap: wrap;
}

.author-link {
  color: #5d4037;
  font-weight: 700;
  text-decoration: none;
}

.author-link:hover {
  color: #a75e63;
}

.username {
  color: #a1887f;
  font-size: 12px;
}

.post-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  color: #aa9188;
  font-size: 12px;
}

.visibility {
  padding: 2px 7px;
  border-radius: 8px;
  background: rgba(248, 187, 208, 0.14);
}

.delete-button {
  border: 0;
  padding: 6px 9px;
  border-radius: 9px;
  color: #a75e63;
  background: transparent;
  cursor: pointer;
}

.delete-button:hover {
  background: #fff1f1;
}

.post-content {
  margin: 19px 0 14px;
  color: #4f3a33;
  line-height: 1.8;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.mood-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 11px;
  color: #79645b;
  background: rgba(255, 248, 245, 0.82);
  font-size: 13px;
}

.post-actions {
  display: flex;
  gap: 8px;
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid rgba(141, 110, 99, 0.1);
}

.post-actions button {
  border: 0;
  padding: 8px 11px;
  border-radius: 11px;
  color: #8d746a;
  background: transparent;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
}

.post-actions button:hover,
.post-actions button.active {
  color: #b45e70;
  background: rgba(248, 187, 208, 0.13);
}

.comments-panel {
  margin-top: 15px;
  padding: 15px;
  border-radius: 17px;
  background: rgba(255, 250, 248, 0.86);
}

.comments-tip {
  padding: 6px 2px 12px;
  color: #a1887f;
  font-size: 13px;
}

.comment-list {
  display: grid;
  gap: 10px;
}

.comment-item {
  padding: 10px 12px;
  border-radius: 12px;
  background: #fff;
}

.comment-item strong {
  color: #6d4c41;
  font-size: 13px;
}

.comment-item p {
  margin: 5px 0;
  color: #5d4840;
  line-height: 1.6;
  font-size: 14px;
  overflow-wrap: anywhere;
}

.comment-item time {
  color: #b09a92;
  font-size: 11px;
}

.comment-form {
  display: flex;
  gap: 8px;
  margin-top: 13px;
}

:deep(.comment-form .el-input__wrapper) {
  border-radius: 12px;
  box-shadow: 0 0 0 1px #f0ded8 inset;
}

.comment-form :deep(.el-button) {
  border-radius: 11px;
  color: #6d4c41;
  border-color: #ead7d0;
  background: #fff;
}

@media (max-width: 560px) {
  .post-card {
    padding: 18px;
    border-radius: 20px;
  }

  .comment-form {
    flex-direction: column;
  }
}
</style>
