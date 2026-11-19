import { api } from './client'

export interface ChatSession {
  id: number
  title: string
  created_at?: string
  updated_at?: string
  last_message?: string | null
}

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  safety_flag: boolean
  created_at?: string
}

export interface ChatStreamEvent {
  event: 'delta' | 'done' | 'error'
  data: {
    content?: string
    message?: string
    message_id?: number
    safety_flag?: boolean
  }
}

export async function fetchSessions() {
  const response = await api.get('/chat/sessions')
  return response.data.data as ChatSession[]
}

export async function createSession(title?: string) {
  const response = await api.post('/chat/sessions', {
    title: title || null,
  })
  return response.data.data as ChatSession
}

export async function fetchMessages(sessionId: number) {
  const response = await api.get(
    `/chat/sessions/${sessionId}/messages`,
  )
  return response.data.data as ChatMessage[]
}

export async function removeSession(sessionId: number) {
  await api.delete(`/chat/sessions/${sessionId}`)
}

function parseEventBlock(block: string): ChatStreamEvent | null {
  let event = ''
  const dataLines: string[] = []

  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim())
    }
  }

  if (!event || dataLines.length === 0) {
    return null
  }

  try {
    return {
      event: event as ChatStreamEvent['event'],
      data: JSON.parse(dataLines.join('\n')),
    }
  } catch {
    return null
  }
}

export async function streamMessage(
  sessionId: number,
  content: string,
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal,
) {
  const baseURL = api.defaults.baseURL || ''
  const response = await fetch(
    `${baseURL}/chat/sessions/${sessionId}/messages/stream`,
    {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify({ content }),
      signal,
    },
  )

  if (!response.ok) {
    let message = '发送消息失败'
    try {
      const data = await response.json()
      if (typeof data.detail === 'string') {
        message = data.detail
      }
    } catch {
      // 使用通用错误信息。
    }
    throw new Error(message)
  }

  if (!response.body) {
    throw new Error('浏览器不支持流式回复')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()

    if (done) {
      break
    }

    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split(/\r?\n\r?\n/)
    buffer = blocks.pop() || ''

    for (const block of blocks) {
      const event = parseEventBlock(block)
      if (event) {
        onEvent(event)
      }
    }
  }

  if (buffer.trim()) {
    const event = parseEventBlock(buffer)
    if (event) {
      onEvent(event)
    }
  }
}
