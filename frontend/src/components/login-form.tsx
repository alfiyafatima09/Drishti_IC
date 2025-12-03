import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Github, Loader2, ArrowRight } from 'lucide-react'
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
              className="text-xs font-light tracking-wider text-zinc-500 uppercase"
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
              className="h-10 rounded-none border-0 border-b border-zinc-200 bg-transparent px-0 transition-colors placeholder:text-zinc-300 focus-visible:border-zinc-900 focus-visible:ring-0 dark:border-zinc-800 dark:placeholder:text-zinc-700 dark:focus-visible:border-zinc-100"
            />
          </div>
          <div className="grid gap-2">
            <div className="flex items-center justify-between">
              <Label
                htmlFor="password"
                className="text-xs font-light tracking-wider text-zinc-500 uppercase"
              >
                Password
              </Label>
              <a
                href="#"
                className="text-[10px] font-medium tracking-widest text-zinc-400 uppercase transition-colors hover:text-zinc-900 dark:hover:text-zinc-100"
              >
                Forgot?
              </a>
            </div>
            <Input
              id="password"
              type="password"
              autoCapitalize="none"
              autoComplete="current-password"
              disabled={isLoading}
              className="h-10 rounded-none border-0 border-b border-zinc-200 bg-transparent px-0 transition-colors focus-visible:border-zinc-900 focus-visible:ring-0 dark:border-zinc-800 dark:focus-visible:border-zinc-100"
            />
          </div>
          <Button
            disabled={isLoading}
            className="mt-4 h-10 bg-zinc-900 font-medium tracking-wide text-zinc-50 transition-all hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-950 dark:hover:bg-zinc-200"
          >
            {isLoading && <Loader2 className="mr-2 h-3 w-3 animate-spin" />}
            Sign In
            {!isLoading && <ArrowRight className="ml-2 h-3 w-3 opacity-50" />}
          </Button>
        </div>
      </form>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t border-zinc-100 dark:border-zinc-800/50" />
        </div>
        <div className="relative flex justify-center text-[10px] tracking-widest uppercase">
          <span className="bg-white px-2 text-zinc-400 dark:bg-zinc-950 dark:text-zinc-600">
            Or
          </span>
        </div>
      </div>

      <Button
        variant="outline"
        type="button"
        disabled={isLoading}
        className="h-10 border-zinc-200 bg-transparent font-normal text-zinc-600 hover:bg-zinc-50 dark:border-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-900 dark:hover:text-zinc-100"
      >
        {isLoading ? (
          <Loader2 className="mr-2 h-3 w-3 animate-spin" />
        ) : (
          <Github className="mr-2 h-3 w-3" />
        )}
        GitHub
      </Button>
    </div>
  )
}
