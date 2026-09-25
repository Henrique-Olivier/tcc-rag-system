import { useQuery } from '@tanstack/react-query'
import { fetchHealth } from '@/api/health'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function HomePage() {
  const health = useQuery({ queryKey: ['health'], queryFn: fetchHealth })

  return (
    <main className="flex min-h-svh items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Assistente de pesquisa TCC</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Estado da API</span>
          {health.isPending && <Badge variant="secondary">verificando...</Badge>}
          {health.isError && <Badge variant="destructive">indisponível ({health.error.message})</Badge>}
          {health.isSuccess && <Badge>{health.data.status}</Badge>}
        </CardContent>
      </Card>
    </main>
  )
}
