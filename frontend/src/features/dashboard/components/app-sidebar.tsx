import {
    Sidebar,
    SidebarContent,
    SidebarFooter,
    SidebarGroup,
    SidebarGroupContent,
    SidebarGroupLabel,
    SidebarHeader,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarRail,
} from '@/components/ui/sidebar'
import {
    LayoutDashboard,
    ScanLine,
    Database,
    History,
    Settings,
    Shield,
    LogOut,
    User,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'

// Menu items.
const items = [
    {
        title: 'Dashboard',
        url: '/dashboard',
        icon: LayoutDashboard,
    },
    {
        title: 'New Scan',
        url: '/dashboard/scan',
        icon: ScanLine,
    },
    {
        title: 'IC Database',
        url: '/dashboard/database',
        icon: Database,
    },
    {
        title: 'Scan History',
        url: '/dashboard/history',
        icon: History,
    },
]

export function AppSidebar() {
    const navigate = useNavigate()

    return (
        <Sidebar collapsible="icon" className="border-r border-zinc-200 dark:border-zinc-800">
            <SidebarHeader className="h-16 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-center px-4 group-data-[collapsible=icon]:px-2">
                <div className="flex items-center gap-2 w-full overflow-hidden transition-all duration-300 group-data-[collapsible=icon]:justify-center">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-zinc-900 dark:bg-zinc-50 text-zinc-50 dark:text-zinc-900">
                        <Shield className="h-4 w-4" />
                    </div>
                    <div className="flex flex-col overflow-hidden transition-all duration-300 group-data-[collapsible=icon]:w-0 group-data-[collapsible=icon]:opacity-0">
                        <span className="font-medium tracking-wide text-zinc-900 dark:text-zinc-50 whitespace-nowrap">
                            Drishti IC
                        </span>
                    </div>
                </div>
            </SidebarHeader>

            <SidebarContent className="gap-0">
                <SidebarGroup className="pt-4">
                    <SidebarGroupLabel className="text-xs font-light uppercase tracking-widest text-zinc-500 dark:text-zinc-400 px-4 mb-2 group-data-[collapsible=icon]:hidden">
                        Platform
                    </SidebarGroupLabel>
                    <SidebarGroupContent>
                        <SidebarMenu className="gap-1 px-2 group-data-[collapsible=icon]:px-0">
                            {items.map((item) => (
                                <SidebarMenuItem key={item.title}>
                                    <SidebarMenuButton
                                        asChild
                                        tooltip={item.title}
                                        className="h-9 hover:bg-zinc-100 dark:hover:bg-zinc-800/50 text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors group-data-[collapsible=icon]:justify-center"
                                    >
                                        <a href={item.url}>
                                            <item.icon className="h-4 w-4 shrink-0" />
                                            <span className="font-light tracking-wide group-data-[collapsible=icon]:hidden">{item.title}</span>
                                        </a>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            ))}
                        </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>

                <SidebarGroup className="mt-auto pb-4">
                    <SidebarGroupContent>
                        <SidebarMenu className="gap-1 px-2 group-data-[collapsible=icon]:px-0">
                            <SidebarMenuItem>
                                <SidebarMenuButton
                                    asChild
                                    tooltip="Settings"
                                    className="h-9 hover:bg-zinc-100 dark:hover:bg-zinc-800/50 text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors group-data-[collapsible=icon]:justify-center"
                                >
                                    <a href="/dashboard/settings">
                                        <Settings className="h-4 w-4 shrink-0" />
                                        <span className="font-light tracking-wide group-data-[collapsible=icon]:hidden">Settings</span>
                                    </a>
                                </SidebarMenuButton>
                            </SidebarMenuItem>
                        </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>
            </SidebarContent>

            <SidebarFooter className="border-t border-zinc-200 dark:border-zinc-800 p-4 group-data-[collapsible=icon]:p-2">
                <SidebarMenu>
                    <SidebarMenuItem>
                        <SidebarMenuButton
                            size="lg"
                            className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground hover:bg-zinc-100 dark:hover:bg-zinc-800/50 transition-colors group-data-[collapsible=icon]:justify-center"
                        >
                            <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 shrink-0">
                                <User className="size-4" />
                            </div>
                            <div className="grid flex-1 text-left text-sm leading-tight group-data-[collapsible=icon]:hidden">
                                <span className="truncate font-medium text-zinc-900 dark:text-zinc-50">Admin User</span>
                                <span className="truncate text-xs text-zinc-500 dark:text-zinc-400">admin@drishti.ic</span>
                            </div>
                            <LogOut className="ml-auto size-4 text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-50 transition-colors group-data-[collapsible=icon]:hidden" onClick={() => navigate('/')} />
                        </SidebarMenuButton>
                    </SidebarMenuItem>
                </SidebarMenu>
            </SidebarFooter>
            <SidebarRail />
        </Sidebar>
    )
}

