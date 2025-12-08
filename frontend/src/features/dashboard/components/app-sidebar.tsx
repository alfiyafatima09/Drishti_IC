import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from '@/components/ui/sidebar'
import { ScanLine, Database, History, Search } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import logo from '@/assets/logo_nobg.png'

import * as React from 'react'

// Menu items
const items = [
  {
    title: 'New Scan',
    url: '/',
    icon: ScanLine,
  },
  {
    title: 'IC Database',
    url: '/database',
    icon: Search,
  },
  {
    title: 'Manage Data',
    url: '/manage',
    icon: Database,
  },
  {
    title: 'Scan History',
    url: '/history',
    icon: History,
  },
]

export function AppSidebar() {
  const location = useLocation()

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
      <SidebarHeader className="flex h-20 items-center justify-center border-b border-cyan-400/50 bg-white/5 px-3 group-data-[collapsible=icon]:px-2">
        <div className="flex w-full items-center gap-3 overflow-hidden transition-all duration-300 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:gap-0">
          <img src={logo} alt="Drishti IC" className="h-14 w-14 shrink-0 object-contain" />
          <div className="flex flex-col overflow-hidden transition-all duration-300 group-data-[collapsible=icon]:w-0 group-data-[collapsible=icon]:opacity-0">
            <span className="text-lg font-bold tracking-tight whitespace-nowrap text-white">
              Drishti IC
            </span>
            <span className="text-xs font-medium text-cyan-200/80">SIH 2025 • BEL</span>
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
              {items.map((item) => {
                const isActive = location.pathname === item.url
                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      asChild
                      isActive={isActive}
                      tooltip={item.title}
                      className={`h-11 rounded-lg font-semibold transition-all group-data-[collapsible=icon]:justify-center ${
                        isActive
                          ? 'bg-white text-blue-600 shadow-lg hover:bg-white hover:text-blue-600'
                          : 'text-white hover:bg-white/20 hover:text-white'
                      }`}
                    >
                      <Link to={item.url}>
                        <item.icon className="h-5 w-5 shrink-0" />
                        <span className="font-semibold tracking-wide group-data-[collapsible=icon]:hidden">
                          {item.title}
                        </span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarRail />
    </Sidebar>
  )
}
