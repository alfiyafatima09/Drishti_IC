import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Loader2, ArrowRight } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export function LoginForm({ className, ...props }: React.ComponentProps<'div'>) {
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const navigate = useNavigate()

  async function onSubmit(event: React.SyntheticEvent) {
    event.preventDefault()
    setIsLoading(true)

    setTimeout(() => {
      setIsLoading(false)
      navigate('/scan')
    }, 1500) // Reduced delay for faster feel
  }

  return (
    <div className={cn('grid gap-8', className)} {...props}>
      <form onSubmit={onSubmit}>
        <div className="grid gap-5">
          <div className="grid gap-2">
            <Label htmlFor="email" className="text-sm font-bold tracking-wide text-blue-700">
              Email Address
            </Label>
            <Input
              id="email"
              placeholder="name@example.com"
              type="email"
              autoCapitalize="none"
              autoComplete="email"
              autoCorrect="off"
              disabled={isLoading}
              className="h-12 rounded-xl border-2 border-blue-300 bg-white px-4 text-base font-medium shadow-sm transition-all placeholder:text-blue-400 hover:border-blue-400 focus:border-cyan-500 focus:bg-blue-50 focus:ring-4 focus:ring-cyan-100"
            />
          </div>
          <div className="grid gap-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="password" className="text-sm font-bold tracking-wide text-blue-700">
                Password
              </Label>
              <a
                href="#"
                className="text-xs font-bold text-cyan-600 transition-colors hover:text-cyan-700"
              >
                Forgot password?
              </a>
            </div>
            <Input
              id="password"
              type="password"
              autoCapitalize="none"
              autoComplete="current-password"
              disabled={isLoading}
              className="h-12 rounded-xl border-2 border-blue-300 bg-white px-4 text-base font-medium shadow-sm transition-all hover:border-blue-400 focus:border-cyan-500 focus:bg-blue-50 focus:ring-4 focus:ring-cyan-100"
            />
          </div>
          <Button
            disabled={isLoading}
            className="mt-2 h-14 rounded-xl bg-gradient-to-r from-blue-600 via-cyan-600 to-blue-700 text-base font-bold text-white shadow-xl transition-all hover:from-blue-700 hover:via-cyan-700 hover:to-blue-800 hover:shadow-2xl active:scale-[0.98]"
          >
            {isLoading && <Loader2 className="mr-2 h-5 w-5 animate-spin" />}
            Sign In
            {!isLoading && <ArrowRight className="ml-2 h-5 w-5" />}
          </Button>
        </div>
      </form>
    </div>
  )
}
