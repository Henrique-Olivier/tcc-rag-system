import { useCurrentConversation } from '@/hooks/useCurrentConversation'

export default function ChatPage() {
  const { ready } = useCurrentConversation()

  return (
    <div className="flex flex-1 items-center justify-center p-8 text-sm text-muted-foreground">
      {ready ? 'Faça uma pergunta sobre os seus documentos.' : 'Preparando…'}
    </div>
  )
}
