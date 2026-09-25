import { request } from './client'

export type DocumentStatus = 'pending' | 'processing' | 'ready' | 'failed'

export type DocumentItem = {
  id: number
  filename: string
  status: DocumentStatus
  error_message: string | null
  num_pages: number | null
  created_at: string
  queue_position: number | null
}

export type UploadOutcome = 'new' | 'duplicate' | 'reprocessed' | 'reactivated' | 'rejected'

export type UploadResult = {
  filename: string
  outcome: UploadOutcome
  document_id: number | null
  message: string | null
}

export const listDocuments = () => request<DocumentItem[]>('/documents')

export function uploadDocuments(files: File[]) {
  const body = new FormData()
  files.forEach((file) => body.append('files', file))
  return request<UploadResult[]>('/documents', { method: 'POST', body })
}

export const deleteDocument = (id: number) => request<void>(`/documents/${id}`, { method: 'DELETE' })
