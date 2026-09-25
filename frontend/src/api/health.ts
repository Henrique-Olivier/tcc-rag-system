import { request } from './client'

export type Health = {
  status: 'ok' | 'degraded'
  database: 'ok' | 'unavailable'
  worker: 'running' | 'stopped' | 'unknown'
  embedding_model: 'ready' | 'loading' | 'failed'
}

export const fetchHealth = () => request<Health>('/health')
