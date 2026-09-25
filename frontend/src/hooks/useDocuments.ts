import { useQuery } from '@tanstack/react-query'
import { listDocuments, type DocumentItem } from '@/api/documents'

export const isWorking = (doc: DocumentItem) => doc.status === 'pending' || doc.status === 'processing'

/** Lista de documentos, consultada a cada 2 s enquanto houver algo na fila (plano, seção 9, v8). */
export function useDocuments() {
  return useQuery({
    queryKey: ['documents'],
    queryFn: listDocuments,
    refetchInterval: (query) => (query.state.data?.some(isWorking) ? 2000 : false),
  })
}
