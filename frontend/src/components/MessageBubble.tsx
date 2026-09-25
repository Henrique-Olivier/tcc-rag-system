import Markdown from 'react-markdown'
import { cn } from '@/lib/utils'

type Props = {
  role: 'user' | 'assistant'
  content: string
  status: 'streaming' | 'complete' | 'error'
  error?: string
}

/** Resposta renderizada como markdown (plano v5). */
export default function MessageBubble({ role, content, status, error }: Props) {
  if (role === 'user') {
    return <div className="ml-auto max-w-[80%] rounded-2xl bg-primary px-4 py-2 text-sm whitespace-pre-wrap text-primary-foreground">{content}</div>
  }
  if (status === 'error') {
    return (
      <div className="max-w-[80%] rounded-2xl border border-destructive/40 px-4 py-2 text-sm">
        <p className="font-medium text-destructive">Resposta não concluída</p>
        {error && <p className="mt-1 text-muted-foreground">{error}</p>}
      </div>
    )
  }
  return (
    <div
      className={cn(
        'max-w-[80%] space-y-2 rounded-2xl bg-muted px-4 py-2 text-sm leading-relaxed',
        '[&_ol]:list-decimal [&_ol]:pl-5 [&_ul]:list-disc [&_ul]:pl-5',
      )}
    >
      {content ? <Markdown>{content}</Markdown> : <p className="text-muted-foreground">Pensando…</p>}
    </div>
  )
}
