import { fetchEventSource } from '@microsoft/fetch-event-source'
import { ApiError, request } from './client'

export type Conversation = {
  id: number
  title: string | null
  created_at: string
  closed_at: string | null
}

/** Trecho enviado no prompt (evento `sources`) ou citação salva (conversa salva). */
export type Source = {
  marker: number
  chunk_id: number | null
  document_id: number
  filename: string
  page_number: number
  excerpt: string
  document_removed?: boolean
}

/** Chamado ao carregar o front: é o "fechar o sistema" do CA13 (plano, seção 7). */
export const closeOpenConversations = () => request<void>('/conversations/close-open', { method: 'POST' })

export const createConversation = () => request<Conversation>('/conversations', { method: 'POST' })

type StreamHandlers = {
  onSources: (sources: Source[]) => void
  onToken: (text: string) => void
  onDone: (markers: number[]) => void
  onError: (message: string) => void
}

/** Pergunta por POST com resposta por SSE (plano, seção 6.5). O EventSource nativo só faz GET. */
export function streamAnswer(conversationId: number, question: string, handlers: StreamHandlers) {
  return fetchEventSource(`/api/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: question }),
    // Sem isso a biblioteca reabre a conexão quando a aba volta a ficar visível e reenviaria a pergunta.
    openWhenHidden: true,
    async onopen(response) {
      if (!response.ok) {
        const body = await response.json().catch(() => null)
        throw new ApiError(response.status, body?.detail ?? `HTTP ${response.status}`)
      }
    },
    onmessage(event) {
      const data = JSON.parse(event.data)
      if (event.event === 'sources') handlers.onSources(data.sources)
      else if (event.event === 'token') handlers.onToken(data.text)
      else if (event.event === 'done') handlers.onDone(data.markers)
      else if (event.event === 'error') handlers.onError(data.message)
    },
    onerror(error) {
      throw error // sem novas tentativas: repetir o POST duplicaria a pergunta
    },
  })
}

export type SavedMessage = {
  id: number
  role: 'user' | 'assistant'
  content: string
  status: 'complete' | 'error'
  created_at: string
  citations: Source[]
}

export type ConversationDetail = Conversation & { messages: SavedMessage[] }

export const listConversations = () => request<Conversation[]>('/conversations')

export const getConversation = (id: number) => request<ConversationDetail>(`/conversations/${id}`)

export const deleteConversation = (id: number) => request<void>(`/conversations/${id}`, { method: 'DELETE' })

export const conversationTitle = (conversation: Conversation) => conversation.title ?? 'Conversa sem título'

export const formatDate = (iso: string) =>
  new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
