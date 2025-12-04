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
import { LayoutDashboard, ScanLine, Database, History, Settings, Shield } from 'lucide-react'

import * as React from 'react'
import { UserNav } from './user-nav'

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
  return (
    <Sidebar
      collapsible="icon"
      className="sidebar-grainy border-r border-zinc-800"
      style={
        {
          '--sidebar': 'transparent',
          '--sidebar-foreground': '#F0F0F0',
          '--sidebar-primary': '#F0F0F0',
          '--sidebar-primary-foreground': '#1a1a1a',
          '--sidebar-accent': '#27272a',
          '--sidebar-accent-foreground': '#F0F0F0',
          '--sidebar-border': '#27272a',
          '--sidebar-ring': '#D0D0D0',
        } as React.CSSProperties
      }
    >
      <SidebarHeader className="flex h-16 items-center justify-center border-b border-zinc-800 px-4 group-data-[collapsible=icon]:px-2">
        <div className="flex w-full items-center gap-2 overflow-hidden transition-all duration-300 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:gap-0">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-zinc-700 bg-zinc-800/50 text-[#F0F0F0]">
            <Shield className="h-4 w-4" />
          </div>
          <div className="flex flex-col overflow-hidden transition-all duration-300 group-data-[collapsible=icon]:w-0 group-data-[collapsible=icon]:opacity-0">
            <span className="font-medium tracking-wide whitespace-nowrap text-[#F0F0F0]">
              Drishti IC
            </span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent className="gap-0">
        <SidebarGroup className="pt-4">
          <SidebarGroupLabel className="mb-2 px-4 text-xs font-light tracking-widest text-[#A0A0A0] uppercase group-data-[collapsible=icon]:hidden">
            Platform
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-1 px-2 group-data-[collapsible=icon]:px-0">
              {items.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    tooltip={item.title}
                    className="h-9 text-[#D0D0D0] transition-colors group-data-[collapsible=icon]:justify-center hover:bg-zinc-800/50 hover:text-[#F0F0F0]"
                  >
                    <a href={item.url}>
                      <item.icon className="h-4 w-4 shrink-0" />
                      <span className="font-light tracking-wide group-data-[collapsible=icon]:hidden">
                        {item.title}
                      </span>
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
                  className="h-9 text-[#D0D0D0] transition-colors group-data-[collapsible=icon]:justify-center hover:bg-zinc-800/50 hover:text-[#F0F0F0]"
                >
                  <a href="/dashboard/settings">
                    <Settings className="h-4 w-4 shrink-0" />
                    <span className="font-light tracking-wide group-data-[collapsible=icon]:hidden">
                      Settings
                    </span>
                  </a>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t border-zinc-800 p-4 group-data-[collapsible=icon]:p-2">
        <SidebarMenu>
          <SidebarMenuItem>
            <UserNav />
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
