import { Outlet } from 'react-router'
import AppSidebar from '@/components/AppSidebar'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'

export default function AppLayout() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="h-svh min-w-0 overflow-hidden">
        <Outlet />
      </SidebarInset>
    </SidebarProvider>
  )
}
