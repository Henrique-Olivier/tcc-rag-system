import { useQuery } from '@tanstack/react-query'
import { fetchHealth } from '../api/health'

export default function HomePage() {
  const health = useQuery({ queryKey: ['health'], queryFn: fetchHealth })

  return (
    <main>
      <h1>Assistente de pesquisa TCC</h1>
      <p>
        Estado da API:{' '}
        {health.isPending && 'verificando...'}
        {health.isError && `indisponível (${health.error.message})`}
        {health.isSuccess && health.data.status}
      </p>
    </main>
  )
}
