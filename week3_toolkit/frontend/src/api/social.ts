import { api } from './client'

export interface SocialPost {
  id: number
  user_id: number
  content: string
  mood: string | null
  visibility: 'private' | 'public'
  created_at: string
  updated_at: string
  username: string
  display_name: string
  avatar_url: string
  reaction_count: number
  comment_count: number
  liked_by_me: boolean
}

export interface SocialComment {
  id: number
  post_id: number
  user_id: number
  content: string
  created_at: string
  username: string
  display_name: string
  avatar_url: string
}

export interface PostPayload {
  content: string
  mood: string | null
  visibility: 'private' | 'public'
}

export interface SocialProfile {
  id: number
  username: string
  display_name: string
  bio: string
  avatar_url: string
  post_count: number
}

export async function fetchFeed(beforeId?: number) {
  const response = await api.get('/social/feed', {
    params: {
      limit: 20,
      ...(beforeId ? { before_id: beforeId } : {}),
    },
  })

  return response.data as {
    status: string
    data: SocialPost[]
    next_cursor: number | null
  }
}

export async function publishPost(payload: PostPayload) {
  const response = await api.post('/social/posts', payload)
  return response.data.data as SocialPost
}

export async function deletePost(postId: number) {
  await api.delete(`/social/posts/${postId}`)
}

export async function likePost(postId: number) {
  const response = await api.post(`/social/posts/${postId}/like`)
  return response.data as {
    liked_by_me: boolean
    reaction_count: number
  }
}

export async function unlikePost(postId: number) {
  const response = await api.delete(`/social/posts/${postId}/like`)
  return response.data as {
    liked_by_me: boolean
    reaction_count: number
  }
}

export async function fetchComments(postId: number) {
  const response = await api.get(`/social/posts/${postId}/comments`)
  return response.data.data as SocialComment[]
}

export async function createComment(postId: number, content: string) {
  const response = await api.post(
    `/social/posts/${postId}/comments`,
    { content },
  )
  return response.data.data as SocialComment
}

export async function fetchProfile(userId: number) {
  const response = await api.get(`/social/profiles/${userId}`)
  return response.data.data as SocialProfile
}

export async function fetchMyProfile() {
  const response = await api.get('/social/profiles/me')
  return response.data.data as SocialProfile
}

export async function updateMyProfile(payload: {
  display_name: string
  bio: string
}) {
  const response = await api.patch('/social/profiles/me', payload)
  return response.data.data as SocialProfile
}

export async function fetchUserPosts(
  userId: number,
  beforeId?: number,
) {
  const response = await api.get(
    `/social/users/${userId}/posts`,
    {
      params: {
        limit: 20,
        ...(beforeId ? { before_id: beforeId } : {}),
      },
    },
  )

  return response.data as {
    status: string
    data: SocialPost[]
    next_cursor: number | null
  }
}
