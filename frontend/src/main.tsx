import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router'
import './index.css'
import AppLayout from '@/components/AppLayout'
import { TooltipProvider } from '@/components/ui/tooltip'
import { CurrentConversationProvider } from '@/hooks/useCurrentConversation'
import ChatPage from '@/pages/ChatPage'
import ConversationPage from '@/pages/ConversationPage'
import DocumentsPage from '@/pages/DocumentsPage'

const queryClient = new QueryClient()

// O id da conversa atual nunca vai para a URL (plano, seção 7); só as salvas, somente leitura, têm rota.
const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: '/', element: <ChatPage /> },
      { path: '/documentos', element: <DocumentsPage /> },
      { path: '/conversas/:id', element: <ConversationPage /> },
    ],
  },
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <CurrentConversationProvider>
        <TooltipProvider>
          <RouterProvider router={router} />
        </TooltipProvider>
      </CurrentConversationProvider>
    </QueryClientProvider>
  </StrictMode>,
)
