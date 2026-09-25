/** Erro HTTP com o status, para tratar casos como o 409 de conversa encerrada (plano, seção 7). */
export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/** O proxy do Vite remove o prefixo /api (plano, seção 11). */
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init)
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(response.status, body?.detail ?? `HTTP ${response.status}`)
  }
  return response.status === 204 ? (undefined as T) : response.json()
}
