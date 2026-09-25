import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'
import type { Source } from '@/api/conversations'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'

pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()

type Props = {
  source: Source
  onClose: () => void
}

/** Abre o PDF na página citada. O react-pdf numera a partir de 1, como o banco (plano, seção 4). */
export default function PdfViewer({ source, onClose }: Props) {
  const [page, setPage] = useState(source.page_number)
  const [pages, setPages] = useState<number | null>(null)

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="flex h-[90svh] max-w-4xl flex-col gap-3 sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle className="truncate">{source.filename}</DialogTitle>
          <DialogDescription>
            Página {page}
            {pages ? ` de ${pages}` : ''} · citada na página {source.page_number}
          </DialogDescription>
        </DialogHeader>
        <div className="min-h-0 flex-1 overflow-auto rounded-md bg-muted">
          <Document
            file={`/api/documents/${source.document_id}/file`}
            onLoadSuccess={({ numPages }) => setPages(numPages)}
            loading={<p className="p-4 text-sm text-muted-foreground">Carregando o PDF…</p>}
            error={<p className="p-4 text-sm text-destructive">Não foi possível abrir o PDF.</p>}
            className="flex justify-center p-4"
          >
            <Page pageNumber={page} width={760} />
          </Document>
        </div>
        <div className="flex items-center justify-center gap-2">
          <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)} aria-label="Página anterior">
            <ChevronLeft />
          </Button>
          <Button size="sm" variant="outline" disabled={pages !== null && page >= pages} onClick={() => setPage(page + 1)} aria-label="Próxima página">
            <ChevronRight />
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
