import {
  DropdownMenu,
  DropdownMenuContent,
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
import { ChevronsUpDown, LogOut, User } from 'lucide-react'
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
            className="text-white transition-colors group-data-[collapsible=icon]:justify-center hover:bg-white/20 hover:text-white data-[state=open]:bg-white/20 data-[state=open]:text-white"
          >
            <div className="flex aspect-square size-8 shrink-0 items-center justify-center rounded-lg border-2 border-cyan-300 bg-white text-blue-600 shadow-sm">
              <User className="size-4" />
            </div>
            <div className="grid flex-1 text-left text-sm leading-tight group-data-[collapsible=icon]:hidden">
              <span className="truncate font-bold">Admin User</span>
              <span className="truncate text-xs font-medium text-cyan-100">admin@drishti.ic</span>
            </div>
            <ChevronsUpDown className="ml-auto size-4 text-cyan-100 group-data-[collapsible=icon]:hidden" />
          </SidebarMenuButton>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          className="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-xl border-2 border-blue-100 bg-white/95 p-2 text-slate-700 shadow-xl backdrop-blur-md"
          side="bottom"
          align="end"
          sideOffset={4}
        >
          <DropdownMenuLabel className="p-0 font-normal">
            <div className="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg border border-blue-100 bg-blue-50 text-blue-600">
                <User className="size-4" />
              </div>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-bold text-slate-800">Admin User</span>
                <span className="truncate text-xs text-slate-500">admin@drishti.ic</span>
              </div>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator className="my-1 bg-blue-100" />
          <DropdownMenuItem
            className="cursor-pointer font-medium text-red-600 focus:bg-red-50 focus:text-red-700"
            onSelect={() => setShowLogoutDialog(true)}
          >
            <LogOut className="mr-2 h-4 w-4" />
            Log out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <AlertDialog open={showLogoutDialog} onOpenChange={setShowLogoutDialog}>
        <AlertDialogContent className="border-2 border-blue-100 bg-white text-slate-800">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-xl font-bold text-slate-900">
              Sign out?
            </AlertDialogTitle>
            <AlertDialogDescription className="text-slate-600">
              Are you sure you want to sign out? You'll need to sign in again to access the
              dashboard.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100 hover:text-slate-900">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleLogout}
              className="bg-red-600 text-white hover:bg-red-700"
            >
              Log out
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
