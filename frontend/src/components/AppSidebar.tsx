import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileText, SquarePen, Trash2 } from 'lucide-react'
import { NavLink, useLocation, useMatch, useNavigate } from 'react-router'
import { conversationTitle, deleteConversation, formatDate, listConversations } from '@/api/conversations'
import ConfirmButton from '@/components/ConfirmButton'
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from '@/components/ui/sidebar'
import { useCurrentConversation } from '@/hooks/useCurrentConversation'
import { useDocuments } from '@/hooks/useDocuments'

/** Navegação e conversas salvas (plano, seção 9, v9); os documentos têm página própria. */
export default function AppSidebar() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const viewing = useMatch('/conversas/:id')?.params.id
  const { conversationId, sending, newConversation } = useCurrentConversation()
  const documents = useDocuments()
  const conversations = useQuery({ queryKey: ['conversations'], queryFn: listConversations })

  const remove = useMutation({
    mutationFn: deleteConversation,
    onSuccess: (_, id) => {
      if (id === conversationId) newConversation()
      if (String(id) === viewing) navigate('/')
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
    },
  })

  return (
    <Sidebar>
      <SidebarHeader className="px-4 py-3 text-sm font-semibold">Assistente de pesquisa TCC</SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  disabled={sending}
                  onClick={() => {
                    newConversation()
                    navigate('/')
                  }}
                >
                  <SquarePen /> Nova conversa
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton asChild isActive={pathname === '/documentos'}>
                  <NavLink to="/documentos">
                    <FileText /> Documentos
                  </NavLink>
                </SidebarMenuButton>
                {documents.data && documents.data.length > 0 && <SidebarMenuBadge>{documents.data.length}</SidebarMenuBadge>}
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Conversas</SidebarGroupLabel>
          <SidebarGroupContent>
            {conversations.isError && <p className="px-2 text-xs text-destructive">Não foi possível carregar as conversas.</p>}
            {conversations.data?.length === 0 && <p className="px-2 text-xs text-muted-foreground">Nenhuma conversa ainda.</p>}
            <SidebarMenu>
              {conversations.data?.map((conversation) => {
                // A conversa em andamento volta para o chat; as outras abrem somente leitura.
                const current = conversation.id === conversationId
                const title = conversationTitle(conversation)
                return (
                  <SidebarMenuItem key={conversation.id}>
                    <SidebarMenuButton
                      asChild
                      size="lg"
                      tooltip={title}
                      isActive={current ? pathname === '/' : viewing === String(conversation.id)}
                    >
                      <NavLink to={current ? '/' : `/conversas/${conversation.id}`}>
                        <span className="flex min-w-0 flex-col">
                          <span className="truncate">{title}</span>
                          <span className="truncate text-xs text-muted-foreground">
                            {formatDate(conversation.created_at)}
                            {current && ' · em andamento'}
                          </span>
                        </span>
                      </NavLink>
                    </SidebarMenuButton>
                    <ConfirmButton
                      trigger={
                        <SidebarMenuAction showOnHover aria-label={`Apagar ${title}`}>
                          <Trash2 />
                        </SidebarMenuAction>
                      }
                      title="Apagar conversa?"
                      description="A conversa e os trechos citados nela são apagados de vez. Isso não pode ser desfeito."
                      confirmLabel="Apagar"
                      onConfirm={() => remove.mutate(conversation.id)}
                    />
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarRail />
    </Sidebar>
  )
}
