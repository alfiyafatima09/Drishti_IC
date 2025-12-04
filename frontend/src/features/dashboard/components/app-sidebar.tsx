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
import { Link } from 'react-router-dom'

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
    url: '/scan',
    icon: ScanLine,
  },
  {
    title: 'IC Database',
    url: '/database',
    icon: Database,
  },
  {
    title: 'Scan History',
    url: '/history',
    icon: History,
  },
]

export function AppSidebar() {
  return (
    <Sidebar
      collapsible="icon"
      className="border-r-2 border-cyan-400 bg-gradient-to-b from-blue-600 to-cyan-600 shadow-2xl"
      style={
        {
          '--sidebar': 'transparent',
          '--sidebar-foreground': '#FFFFFF',
          '--sidebar-primary': '#FFFFFF',
          '--sidebar-primary-foreground': '#0369a1',
          '--sidebar-accent': '#0891b2',
          '--sidebar-accent-foreground': '#FFFFFF',
          '--sidebar-border': '#38bdf8',
          '--sidebar-ring': '#22d3ee',
        } as React.CSSProperties
      }
    >
      <SidebarHeader className="flex h-20 items-center justify-center border-b-2 border-cyan-400 px-4 group-data-[collapsible=icon]:px-2 bg-white/10 backdrop-blur-sm">
        <div className="flex w-full items-center gap-3 overflow-hidden transition-all duration-300 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:gap-0">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border-2 border-cyan-300 bg-white shadow-lg">
            <Shield className="h-6 w-6 text-blue-600" />
          </div>
          <div className="flex flex-col overflow-hidden transition-all duration-300 group-data-[collapsible=icon]:w-0 group-data-[collapsible=icon]:opacity-0">
            <span className="font-black text-lg tracking-tight whitespace-nowrap text-white">
              Drishti IC
            </span>
            <span className="text-xs font-semibold text-cyan-200">
              SIH 2025 • BEL
            </span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent className="gap-0">
        <SidebarGroup className="pt-6">
          <SidebarGroupLabel className="mb-3 px-4 text-xs font-bold tracking-widest text-cyan-200 uppercase group-data-[collapsible=icon]:hidden">
            Navigation
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-2 px-3 group-data-[collapsible=icon]:px-0">
              {items.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    tooltip={item.title}
                    className="h-11 text-white font-semibold transition-all group-data-[collapsible=icon]:justify-center hover:bg-white/20 hover:text-white rounded-lg"
                  >
                    <Link to={item.url}>
                      <item.icon className="h-5 w-5 shrink-0" />
                      <span className="font-semibold tracking-wide group-data-[collapsible=icon]:hidden">
                        {item.title}
                      </span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="mt-auto pb-4">
          <SidebarGroupContent>
            <SidebarMenu className="gap-2 px-3 group-data-[collapsible=icon]:px-0">
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  tooltip="Settings"
                  className="h-11 text-white font-semibold transition-all group-data-[collapsible=icon]:justify-center hover:bg-white/20 hover:text-white rounded-lg"
                >
                  <Link to="/settings">
                    <Settings className="h-5 w-5 shrink-0" />
                    <span className="font-semibold tracking-wide group-data-[collapsible=icon]:hidden">
                      Settings
                    </span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t-2 border-cyan-400 p-4 group-data-[collapsible=icon]:p-2 bg-white/10 backdrop-blur-sm">
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
