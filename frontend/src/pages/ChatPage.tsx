import { SendHorizontal, SquarePen } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import MessageBubble from '@/components/MessageBubble'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useCurrentConversation } from '@/hooks/useCurrentConversation'

export default function ChatPage() {
  const { messages, ready, sending, closedElsewhere, send, newConversation } = useCurrentConversation()
  const [question, setQuestion] = useState('')
  const bottom = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: 'end' })
  }, [messages])

  const submit = async (event?: FormEvent) => {
    event?.preventDefault()
    const text = question.trim()
    if (!text || sending || !ready || closedElsewhere) return
    setQuestion('')
    if ((await send(text)) === 'closed') setQuestion(text) // a pergunta não se perde (seção 7)
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) submit(event)
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="flex items-center justify-between border-b px-4 py-2">
        <h2 className="text-sm font-medium">Nova pergunta</h2>
        <Button size="sm" variant="ghost" onClick={newConversation} disabled={sending}>
          <SquarePen /> Nova conversa
        </Button>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-3xl flex-col gap-4 p-4">
          {messages.length === 0 && (
            <p className="mt-16 text-center text-sm text-muted-foreground">
              {ready ? 'Faça uma pergunta sobre os seus documentos.' : 'Preparando…'}
            </p>
          )}
          {messages.map((message) => (
            <MessageBubble key={message.key} role={message.role} content={message.content} status={message.status} error={message.error} />
          ))}
          <div ref={bottom} />
        </div>
      </div>

      <div className="mx-auto w-full max-w-3xl space-y-2 p-4">
        {closedElsewhere && (
          <Alert>
            <AlertDescription className="flex flex-wrap items-center justify-between gap-2">
              <span>
                Esta conversa foi encerrada, provavelmente porque o sistema foi aberto em outra aba. Comece uma nova conversa.
              </span>
              <Button size="sm" onClick={newConversation}>
                Nova conversa
              </Button>
            </AlertDescription>
          </Alert>
        )}
        <form onSubmit={submit} className="flex items-end gap-2">
          <Textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Pergunte sobre os seus documentos…"
            maxLength={2000}
            rows={2}
            className="max-h-40 resize-none"
            aria-label="Pergunta"
          />
          <Button type="submit" size="icon" disabled={!question.trim() || sending || !ready || closedElsewhere} aria-label="Enviar">
            <SendHorizontal />
          </Button>
        </form>
      </div>
    </div>
  )
}
