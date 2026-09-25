import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileText, Trash2, Upload } from 'lucide-react'
import { useRef, useState, type DragEvent } from 'react'
import { deleteDocument, uploadDocuments, type DocumentItem, type UploadOutcome, type UploadResult } from '@/api/documents'
import { fetchHealth } from '@/api/health'
import ConfirmButton from '@/components/ConfirmButton'
import PageHeader from '@/components/PageHeader'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { isWorking, useDocuments } from '@/hooks/useDocuments'
import { cn } from '@/lib/utils'

const OUTCOME_LABEL: Record<UploadOutcome, string> = {
  new: 'enviado',
  duplicate: 'já existe, não foi indexado de novo',
  reprocessed: 'enviado para processar de novo',
  reactivated: 'reativado',
  rejected: 'recusado',
}

function statusLabel(doc: DocumentItem): string {
  switch (doc.status) {
    case 'pending':
      return doc.queue_position ? `aguardando, ${doc.queue_position}º na fila` : 'aguardando'
    case 'processing':
      return 'processando…'
    case 'ready':
      return doc.num_pages ? `disponível · ${doc.num_pages} páginas` : 'disponível'
    case 'failed':
      return doc.error_message ?? 'não foi possível ler o arquivo'
  }
}

/** Upload e lista de documentos, com a largura toda para nomes longos (plano, seção 9, v9). */
export default function DocumentsPage() {
  const queryClient = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [results, setResults] = useState<UploadResult[]>([])

  const documents = useDocuments()
  const working = documents.data?.some(isWorking) ?? false
  // Health só enquanto há documentos na fila, para avisar se o worker parou (seção 5.5).
  const health = useQuery({ queryKey: ['health'], queryFn: fetchHealth, enabled: working, refetchInterval: working ? 10_000 : false })

  const upload = useMutation({
    mutationFn: uploadDocuments,
    onSuccess: (data) => {
      setResults(data)
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
  })
  const remove = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents'] }),
  })

  const send = (files: FileList | null) => {
    if (files?.length) upload.mutate(Array.from(files))
  }
  const onDrop = (event: DragEvent) => {
    event.preventDefault()
    setDragging(false)
    send(event.dataTransfer.files)
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <PageHeader>
        <h2 className="text-sm font-medium">Documentos</h2>
      </PageHeader>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-4 p-4">
          <div
            onDragOver={(event) => {
              event.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            className={cn(
              'flex flex-col items-center gap-2 rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground transition-colors',
              dragging && 'border-primary bg-primary/5',
            )}
          >
            <Upload className="size-5" aria-hidden />
            <span>Arraste um ou mais PDFs para cá</span>
            <Button variant="outline" disabled={upload.isPending} onClick={() => input.current?.click()}>
              {upload.isPending ? 'Enviando…' : 'Selecionar arquivos'}
            </Button>
            <input
              ref={input}
              type="file"
              accept="application/pdf,.pdf"
              multiple
              hidden
              onChange={(event) => {
                send(event.target.files)
                event.target.value = ''
              }}
            />
          </div>

          {upload.isError && (
            <Alert variant="destructive">
              <AlertDescription>Não foi possível enviar os arquivos: {upload.error.message}</AlertDescription>
            </Alert>
          )}

          {results.length > 0 && (
            <div className="rounded-md bg-muted/50 p-3 text-sm">
              <ul className="space-y-1" aria-label="Resultado do envio">
                {results.map((result, index) => (
                  <li key={`${result.filename}-${index}`} className="[overflow-wrap:anywhere]">
                    <span className="font-medium">{result.filename}</span>: {OUTCOME_LABEL[result.outcome]}
                    {result.message && ` (${result.message})`}
                  </li>
                ))}
              </ul>
              <button type="button" className="mt-2 text-xs text-muted-foreground underline" onClick={() => setResults([])}>
                limpar
              </button>
            </div>
          )}

          {working && health.data && health.data.worker !== 'running' && (
            <Alert variant="destructive">
              <AlertDescription>
                O processamento de documentos está parado. Os arquivos na fila serão processados quando ele voltar.
              </AlertDescription>
            </Alert>
          )}

          {documents.isError && <p className="text-sm text-destructive">Não foi possível carregar os documentos.</p>}
          {documents.data?.length === 0 && <p className="text-sm text-muted-foreground">Nenhum documento enviado ainda.</p>}

          <ul className="divide-y rounded-lg border">
            {documents.data?.map((doc) => (
              <li key={doc.id} className="flex items-start gap-3 p-3">
                <FileText className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
                <div className="min-w-0 flex-1">
                  {/* Nomes como "15+1810+4183+-+Doença..." não têm espaços: quebra em qualquer ponto. */}
                  <p className="text-sm [overflow-wrap:anywhere]">{doc.filename}</p>
                  <p className={cn('text-xs text-muted-foreground', doc.status === 'failed' && 'text-destructive')}>
                    {statusLabel(doc)}
                  </p>
                </div>
                <ConfirmButton
                  trigger={
                    <Button size="icon" variant="ghost" className="size-8 shrink-0" aria-label={`Remover ${doc.filename}`}>
                      <Trash2 className="size-4" />
                    </Button>
                  }
                  title="Remover documento?"
                  description="Ele deixa de ser usado nas respostas. Citações dele em conversas salvas continuam visíveis, com aviso de remoção. Se enviar o mesmo arquivo de novo, ele é reativado."
                  confirmLabel="Remover"
                  onConfirm={() => remove.mutate(doc.id)}
                />
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
