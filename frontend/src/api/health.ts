export type Health = { status: string }

export async function fetchHealth(): Promise<Health> {
  const response = await fetch('/api/health')
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}
