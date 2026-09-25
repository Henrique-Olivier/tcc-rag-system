import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { MessageSquare, Trash2 } from 'lucide-react'
import { NavLink, useMatch, useNavigate } from 'react-router'
import { conversationTitle, deleteConversation, formatDate, listConversations } from '@/api/conversations'
import ConfirmButton from '@/components/ConfirmButton'
import { Button } from '@/components/ui/button'
import { useCurrentConversation } from '@/hooks/useCurrentConversation'
import { cn } from '@/lib/utils'

/** Lista de conversas salvas com data e título (CA14) e exclusão (CA15). */
export default function ConversationsSection() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const viewing = useMatch('/conversas/:id')?.params.id
  const { conversationId, newConversation } = useCurrentConversation()
  const conversations = useQuery({ queryKey: ['conversations'], queryFn: listConversations })

  const remove = useMutation({
    mutationFn: deleteConversation,
    onSuccess: (_, id) => {
      if (id === conversationId) newConversation()
      if (String(id) === viewing) navigate('/')
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
    },
  })

  if (conversations.isError) return <p className="text-xs text-destructive">Não foi possível carregar as conversas.</p>
  if (conversations.data?.length === 0) return <p className="text-xs text-muted-foreground">Nenhuma conversa ainda.</p>

  return (
    <ul className="space-y-1">
      {conversations.data?.map((conversation) => {
        // A conversa em andamento volta para o chat; as outras abrem somente leitura.
        const current = conversation.id === conversationId
        return (
          <li key={conversation.id} className="flex items-start gap-1">
            <NavLink
              to={current ? '/' : `/conversas/${conversation.id}`}
              className={({ isActive }) =>
                cn('flex min-w-0 flex-1 items-start gap-2 rounded-md px-1 py-1.5 hover:bg-muted/50', isActive && !current && 'bg-muted')
              }
            >
              <MessageSquare className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
              <span className="min-w-0">
                <span className="block truncate text-sm">{conversationTitle(conversation)}</span>
                <span className="block text-xs text-muted-foreground">
                  {formatDate(conversation.created_at)}
                  {current && ' · em andamento'}
                </span>
              </span>
            </NavLink>
            <ConfirmButton
              trigger={
                <Button size="icon" variant="ghost" className="size-7 shrink-0" aria-label={`Apagar ${conversationTitle(conversation)}`}>
                  <Trash2 className="size-3.5" />
                </Button>
              }
              title="Apagar conversa?"
              description="A conversa e os trechos citados nela são apagados de vez. Isso não pode ser desfeito."
              confirmLabel="Apagar"
              onConfirm={() => remove.mutate(conversation.id)}
            />
          </li>
        )
      })}
    </ul>
  )
}
