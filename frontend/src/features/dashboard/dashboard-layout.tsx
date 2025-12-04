import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import { AppSidebar } from './components/app-sidebar'
import { Outlet } from 'react-router-dom'
import { Separator } from '@/components/ui/separator'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb'

export default function DashboardLayout() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="bg-white dark:bg-zinc-950">
        <header className="flex h-16 shrink-0 items-center gap-2 border-b border-zinc-200 px-4 transition-[width,height] ease-linear group-has-[[data-collapsible=icon]]/sidebar-wrapper:h-16 dark:border-zinc-800">
          <div className="flex items-center gap-2 px-4">
            <SidebarTrigger className="-ml-1 h-8 w-8 text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-50" />
            <Separator orientation="vertical" className="mr-2 h-4 bg-zinc-200 dark:bg-zinc-800" />
            <Breadcrumb>
              <BreadcrumbList>
                <BreadcrumbItem className="hidden md:block">
                  <BreadcrumbLink
                    href="#"
                    className="text-zinc-500 transition-colors hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-50"
                  >
                    Platform
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator className="hidden text-zinc-400 md:block dark:text-zinc-600" />
                <BreadcrumbItem>
                  <BreadcrumbPage className="font-medium text-zinc-900 dark:text-zinc-50">
                    Dashboard
                  </BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
          </div>
        </header>
        <div className="flex flex-1 flex-col gap-4 p-4 pt-0">
          <Outlet />
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
