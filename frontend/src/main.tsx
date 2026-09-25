import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router'
import './index.css'
import HomePage from '@/pages/HomePage'

const queryClient = new QueryClient()

// O id da conversa atual nunca vai para a URL (plano, seção 7).
const router = createBrowserRouter([{ path: '/', element: <HomePage /> }])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
)
