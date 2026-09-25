import { Outlet } from 'react-router'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'

export default function AppLayout() {
  return (
    <div className="flex h-svh bg-background text-foreground">
      <aside className="flex w-80 shrink-0 flex-col border-r bg-muted/30">
        <div className="px-4 py-3">
          <h1 className="text-sm font-semibold">Assistente de pesquisa TCC</h1>
        </div>
        <Separator />
        <ScrollArea className="min-h-0 flex-1">
          <section className="p-4">
            <h2 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Documentos</h2>
          </section>
          <Separator />
          <section className="p-4">
            <h2 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Conversas</h2>
          </section>
        </ScrollArea>
      </aside>
      <main className="flex min-w-0 flex-1 flex-col">
        <Outlet />
      </main>
    </div>
  )
}
