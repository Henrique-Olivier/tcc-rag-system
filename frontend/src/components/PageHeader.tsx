import type { ReactNode } from 'react'
import { Separator } from '@/components/ui/separator'
import { SidebarTrigger } from '@/components/ui/sidebar'

/** Barra do topo de cada página, com o botão que abre e fecha a barra lateral. */
export default function PageHeader({ children }: { children: ReactNode }) {
  return (
    <header className="flex h-12 shrink-0 items-center gap-2 border-b px-3">
      <SidebarTrigger />
      <Separator orientation="vertical" className="mr-1 data-[orientation=vertical]:h-4" />
      <div className="flex min-w-0 flex-1 items-center justify-between gap-2">{children}</div>
    </header>
  )
}
