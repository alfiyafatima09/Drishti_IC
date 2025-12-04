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
      navigate('/dashboard')
    }, 1500) // Reduced delay for faster feel
  }

  return (
    <div className={cn('grid gap-8', className)} {...props}>
      <form onSubmit={onSubmit}>
        <div className="grid gap-5">
          <div className="grid gap-2">
            <Label
              htmlFor="email"
              className="text-xs font-medium tracking-wide text-zinc-500"
            >
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
              className="h-11 rounded-xl border-zinc-200 bg-zinc-50/50 px-4 text-sm transition-all placeholder:text-zinc-400 hover:bg-zinc-100/50 focus:border-zinc-400 focus:bg-white focus:ring-4 focus:ring-zinc-100"
            />
          </div>
          <div className="grid gap-2">
            <div className="flex items-center justify-between">
              <Label
                htmlFor="password"
                className="text-xs font-medium tracking-wide text-zinc-500"
              >
                Password
              </Label>
              <a
                href="#"
                className="text-xs font-medium text-zinc-500 transition-colors hover:text-zinc-900"
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
              className="h-11 rounded-xl border-zinc-200 bg-zinc-50/50 px-4 text-sm transition-all hover:bg-zinc-100/50 focus:border-zinc-400 focus:bg-white focus:ring-4 focus:ring-zinc-100"
            />
          </div>
          <Button
            disabled={isLoading}
            className="mt-2 h-11 rounded-xl bg-zinc-900 text-sm font-medium text-white transition-all hover:bg-zinc-800 hover:shadow-lg hover:shadow-zinc-200 active:scale-[0.98]"
          >
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Sign In
            {!isLoading && <ArrowRight className="ml-2 h-4 w-4 opacity-50" />}
          </Button>
        </div>
      </form>

    </div>
  )
}
