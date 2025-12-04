import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { SidebarMenuButton } from '@/components/ui/sidebar'
import { BadgeCheck, Bell, ChevronsUpDown, CreditCard, LogOut, Sparkles, User } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export function UserNav() {
  const navigate = useNavigate()
  const [showLogoutDialog, setShowLogoutDialog] = useState(false)

  const handleLogout = () => {
    setShowLogoutDialog(false)
    navigate('/')
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <SidebarMenuButton
            size="lg"
            className="transition-colors group-data-[collapsible=icon]:justify-center hover:bg-zinc-800/50 data-[state=open]:bg-zinc-800/50 data-[state=open]:text-[#F0F0F0]"
          >
            <div className="flex aspect-square size-8 shrink-0 items-center justify-center rounded-lg border border-zinc-700 bg-zinc-800 text-[#D0D0D0]">
              <User className="size-4" />
            </div>
            <div className="grid flex-1 text-left text-sm leading-tight group-data-[collapsible=icon]:hidden">
              <span className="truncate font-medium text-[#F0F0F0]">Admin User</span>
              <span className="truncate text-xs text-[#A0A0A0]">admin@drishti.ic</span>
            </div>
            <ChevronsUpDown className="ml-auto size-4 text-[#777777] group-data-[collapsible=icon]:hidden" />
          </SidebarMenuButton>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          className="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg border-zinc-800 bg-[#1a1a1a] text-[#F0F0F0]"
          side="bottom"
          align="end"
          sideOffset={4}
        >
          <DropdownMenuLabel className="p-0 font-normal">
            <div className="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg border border-zinc-700 bg-zinc-800 text-[#D0D0D0]">
                <User className="size-4" />
              </div>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-medium">Admin User</span>
                <span className="truncate text-xs text-[#A0A0A0]">admin@drishti.ic</span>
              </div>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator className="bg-zinc-800" />
          <DropdownMenuGroup>
            <DropdownMenuItem className="focus:bg-zinc-800 focus:text-[#F0F0F0]">
              <Sparkles className="mr-2 h-4 w-4" />
              Upgrade to Pro
            </DropdownMenuItem>
          </DropdownMenuGroup>
          <DropdownMenuSeparator className="bg-zinc-800" />
          <DropdownMenuGroup>
            <DropdownMenuItem className="focus:bg-zinc-800 focus:text-[#F0F0F0]">
              <BadgeCheck className="mr-2 h-4 w-4" />
              Account
            </DropdownMenuItem>
            <DropdownMenuItem className="focus:bg-zinc-800 focus:text-[#F0F0F0]">
              <CreditCard className="mr-2 h-4 w-4" />
              Billing
            </DropdownMenuItem>
            <DropdownMenuItem className="focus:bg-zinc-800 focus:text-[#F0F0F0]">
              <Bell className="mr-2 h-4 w-4" />
              Notifications
            </DropdownMenuItem>
          </DropdownMenuGroup>
          <DropdownMenuSeparator className="bg-zinc-800" />
          <DropdownMenuItem
            className="text-red-400 focus:bg-zinc-800 focus:text-[#F0F0F0] focus:text-red-400"
            onSelect={() => setShowLogoutDialog(true)}
          >
            <LogOut className="mr-2 h-4 w-4" />
            Log out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <AlertDialog open={showLogoutDialog} onOpenChange={setShowLogoutDialog}>
        <AlertDialogContent className="border-zinc-800 bg-[#1a1a1a] text-[#F0F0F0]">
          <AlertDialogHeader>
            <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
            <AlertDialogDescription className="text-[#A0A0A0]">
              This action will log you out of your account. You will need to sign in again to access
              the dashboard.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-zinc-700 bg-transparent text-[#F0F0F0] hover:bg-zinc-800 hover:text-[#F0F0F0]">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleLogout}
              className="bg-zinc-50 text-zinc-900 hover:bg-zinc-200"
            >
              Log out
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
