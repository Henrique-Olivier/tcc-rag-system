import Markdown from 'react-markdown'
import type { Source } from '@/api/conversations'
import { CITE_PREFIX, linkMarkers } from '@/lib/citations'
import { cn } from '@/lib/utils'

type Props = {
  role: 'user' | 'assistant'
  content: string
  status: 'streaming' | 'complete' | 'error'
  error?: string
  sources: Source[]
  onCite: (source: Source) => void
}

/** Resposta renderizada como markdown (plano v5), com marcadores [n] clicáveis (seção 9). */
export default function MessageBubble({ role, content, status, error, sources, onCite }: Props) {
  if (role === 'user') {
    return (
      <div className="ml-auto max-w-[80%] rounded-2xl bg-primary px-4 py-2 text-sm whitespace-pre-wrap text-primary-foreground">
        {content}
      </div>
    )
  }
  if (status === 'error') {
    return (
      <div className="max-w-[80%] rounded-2xl border border-destructive/40 px-4 py-2 text-sm">
        <p className="font-medium text-destructive">Resposta não concluída</p>
        {error && <p className="mt-1 text-muted-foreground">{error}</p>}
      </div>
    )
  }
  const byMarker = new Map(sources.map((source) => [source.marker, source]))
  return (
    <div
      className={cn(
        'max-w-[80%] space-y-2 rounded-2xl bg-muted px-4 py-2 text-sm leading-relaxed',
        '[&_ol]:list-decimal [&_ol]:pl-5 [&_ul]:list-disc [&_ul]:pl-5',
      )}
    >
      {content ? (
        <Markdown
          components={{
            a: ({ href, children }) => {
              const source = href?.startsWith(CITE_PREFIX) ? byMarker.get(Number(href.slice(CITE_PREFIX.length))) : undefined
              if (!source) {
                return (
                  <a href={href} target="_blank" rel="noreferrer" className="underline">
                    {children}
                  </a>
                )
              }
              return (
                <button
                  type="button"
                  onClick={() => onCite(source)}
                  title={`${source.filename}, p. ${source.page_number}`}
                  className="mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded-md bg-background px-1 align-baseline text-[11px] font-medium text-primary ring-1 ring-border hover:bg-primary hover:text-primary-foreground"
                >
                  {source.marker}
                </button>
              )
            },
          }}
        >
          {linkMarkers(content, new Set(byMarker.keys()))}
        </Markdown>
      ) : (
        <p className="text-muted-foreground">Pensando…</p>
      )}
    </div>
  )
}
