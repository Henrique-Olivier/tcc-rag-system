import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useParams } from 'react-router'
import { conversationTitle, formatDate, getConversation, type Source } from '@/api/conversations'
import CitationPanel from '@/components/CitationPanel'
import MessageBubble from '@/components/MessageBubble'
import { Badge } from '@/components/ui/badge'

/** Conversa salva, somente leitura: sem campo de pergunta (plano, seção 9). */
export default function ConversationPage() {
  const id = Number(useParams().id)
  const [cited, setCited] = useState<Source | null>(null)
  const conversation = useQuery({ queryKey: ['conversation', id], queryFn: () => getConversation(id) })

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="flex items-center justify-between gap-2 border-b px-4 py-2">
        <div className="min-w-0">
          <h2 className="truncate text-sm font-medium">{conversation.data ? conversationTitle(conversation.data) : 'Conversa'}</h2>
          {conversation.data && <p className="text-xs text-muted-foreground">{formatDate(conversation.data.created_at)}</p>}
        </div>
        <Badge variant="secondary">Somente leitura</Badge>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-3xl flex-col gap-4 p-4">
          {conversation.isPending && <p className="text-sm text-muted-foreground">Carregando…</p>}
          {conversation.isError && <p className="text-sm text-destructive">Conversa não encontrada.</p>}
          {conversation.data?.messages.map((message) => (
            <MessageBubble
              key={message.id}
              role={message.role}
              content={message.content}
              status={message.status}
              sources={message.citations}
              onCite={setCited}
            />
          ))}
        </div>
      </div>
      <CitationPanel source={cited} onClose={() => setCited(null)} />
    </div>
  )
}
