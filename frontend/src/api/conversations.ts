import { request } from './client'

/** Chamado ao carregar o front: é o "fechar o sistema" do CA13 (plano, seção 7). */
export const closeOpenConversations = () => request<void>('/conversations/close-open', { method: 'POST' })
