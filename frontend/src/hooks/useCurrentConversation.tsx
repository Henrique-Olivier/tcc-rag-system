import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { closeOpenConversations } from '@/api/conversations'

type CurrentConversation = {
  /** Só em memória: nunca em localStorage, sessionStorage ou URL (plano, seção 7). */
  conversationId: number | null
  setConversationId: (id: number | null) => void
  /** Verdadeiro depois do close-open inicial; antes disso o chat não envia perguntas. */
  ready: boolean
}

const Context = createContext<CurrentConversation | null>(null)

export function CurrentConversationProvider({ children }: { children: ReactNode }) {
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    // Idempotente: o StrictMode chamar duas vezes não muda nada.
    closeOpenConversations().finally(() => setReady(true))
  }, [])

  return <Context.Provider value={{ conversationId, setConversationId, ready }}>{children}</Context.Provider>
}

export function useCurrentConversation(): CurrentConversation {
  const value = useContext(Context)
  if (!value) throw new Error('useCurrentConversation fora do CurrentConversationProvider')
  return value
}
