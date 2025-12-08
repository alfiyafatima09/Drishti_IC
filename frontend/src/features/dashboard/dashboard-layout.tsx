import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { AppSidebar } from './components/app-sidebar'
import { Outlet } from 'react-router-dom'

export default function DashboardLayout() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="bg-gradient-to-br from-blue-50 via-cyan-50 to-blue-100">
        <div className="flex h-full flex-1 flex-col p-0">
          <Outlet />
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
