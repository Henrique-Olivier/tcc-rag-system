import { FileText } from 'lucide-react'
import { lazy, Suspense, useState } from 'react'
import type { Source } from '@/api/conversations'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'

// O pdf.js é pesado: só carrega quando ela abre um PDF.
const PdfViewer = lazy(() => import('@/components/PdfViewer'))

type Props = {
  source: Source | null
  onClose: () => void
}

/** Painel com o trecho original, o arquivo e a página de uma citação (CA07, CA16). */
export default function CitationPanel({ source, onClose }: Props) {
  const [viewing, setViewing] = useState<Source | null>(null)

  return (
    <>
      <Sheet open={source !== null} onOpenChange={(open) => !open && onClose()}>
        <SheetContent className="gap-0 sm:max-w-md">
          {source && (
            <>
              <SheetHeader>
                <SheetTitle>Trecho citado [{source.marker}]</SheetTitle>
                <SheetDescription className="flex items-center gap-1.5">
                  <FileText className="size-3.5 shrink-0" aria-hidden />
                  <span className="truncate">{source.filename}</span>
                  <span className="shrink-0">· p. {source.page_number}</span>
                </SheetDescription>
              </SheetHeader>
              <div className="space-y-4 overflow-y-auto px-4 pb-4">
                {source.document_removed && (
                  <Alert>
                    <AlertDescription>
                      Este documento foi removido. O trecho abaixo é a cópia salva nesta conversa.
                    </AlertDescription>
                  </Alert>
                )}
                <blockquote className="border-l-2 pl-3 text-sm leading-relaxed whitespace-pre-wrap text-muted-foreground">
                  {source.excerpt}
                </blockquote>
                {!source.document_removed && (
                  <Button onClick={() => setViewing(source)}>Abrir o PDF na página {source.page_number}</Button>
                )}
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
      {viewing && (
        <Suspense fallback={null}>
          <PdfViewer source={viewing} onClose={() => setViewing(null)} />
        </Suspense>
      )}
    </>
  )
}
