import { useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { ApiError } from '@/api/client'
import { closeOpenConversations, createConversation, streamAnswer, type Source } from '@/api/conversations'

export type ChatMessage = {
  key: number
  role: 'user' | 'assistant'
  content: string
  status: 'streaming' | 'complete' | 'error'
  sources: Source[]
  error?: string
}

export type SendResult = 'sent' | 'closed'

type CurrentConversation = {
  /** Só em memória: nunca em localStorage, sessionStorage ou URL (plano, seção 7). */
  conversationId: number | null
  messages: ChatMessage[]
  /** Verdadeiro depois do close-open inicial; antes disso o chat não envia perguntas. */
  ready: boolean
  sending: boolean
  /** A conversa foi encerrada por outra aba (409). */
  closedElsewhere: boolean
  send: (question: string) => Promise<SendResult>
  newConversation: () => void
}

const Context = createContext<CurrentConversation | null>(null)

let nextKey = 0

export function CurrentConversationProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [ready, setReady] = useState(false)
  const [sending, setSending] = useState(false)
  const [closedElsewhere, setClosedElsewhere] = useState(false)

  useEffect(() => {
    // Idempotente: o StrictMode chamar duas vezes não muda nada.
    closeOpenConversations().finally(() => setReady(true))
  }, [])

  const newConversation = useCallback(() => {
    setConversationId(null)
    setMessages([])
    setClosedElsewhere(false)
  }, [])

  const send = useCallback(
    async (question: string): Promise<SendResult> => {
      setSending(true)
      const userKey = nextKey++
      const answerKey = nextKey++
      const updateAnswer = (change: (message: ChatMessage) => ChatMessage) =>
        setMessages((all) => all.map((m) => (m.key === answerKey ? change(m) : m)))
      setMessages((all) => [
        ...all,
        { key: userKey, role: 'user', content: question, status: 'complete', sources: [] },
        { key: answerKey, role: 'assistant', content: '', status: 'streaming', sources: [] },
      ])
      try {
        // A primeira mensagem da sessão cria a conversa, fechando qualquer outra (seção 7).
        const id = conversationId ?? (await createConversation()).id
        setConversationId(id)
        await streamAnswer(id, question, {
          onSources: (sources) => updateAnswer((m) => ({ ...m, sources })),
          onToken: (text) => updateAnswer((m) => ({ ...m, content: m.content + text })),
          onDone: () => updateAnswer((m) => ({ ...m, status: 'complete' })),
          onError: (error) => updateAnswer((m) => ({ ...m, status: 'error', content: '', error })),
        })
        return 'sent'
      } catch (error) {
        if (error instanceof ApiError && error.status === 409) {
          // A pergunta não foi salva: sai da tela e volta para o campo (seção 7).
          setMessages((all) => all.filter((m) => m.key !== userKey && m.key !== answerKey))
          setClosedElsewhere(true)
          return 'closed'
        }
        const message = error instanceof Error ? error.message : 'erro desconhecido'
        updateAnswer((m) => ({ ...m, status: 'error', content: '', error: `Não foi possível obter a resposta (${message}).` }))
        return 'sent'
      } finally {
        setSending(false)
        queryClient.invalidateQueries({ queryKey: ['conversations'] })
      }
    },
    [conversationId, queryClient],
  )

  return (
    <Context.Provider value={{ conversationId, messages, ready, sending, closedElsewhere, send, newConversation }}>
      {children}
    </Context.Provider>
  )
}

export function useCurrentConversation(): CurrentConversation {
  const value = useContext(Context)
  if (!value) throw new Error('useCurrentConversation fora do CurrentConversationProvider')
  return value
}
