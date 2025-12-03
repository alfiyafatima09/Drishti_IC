import { LoginForm } from '@/components/login-form'
import { LoginHero } from './login-hero'

export function LoginPage() {
  return (
    <div className="flex min-h-screen w-full bg-white dark:bg-zinc-950">
      <LoginHero />

      {/* Right Side - Login Form */}
      <div className="flex flex-1 items-center justify-center p-8 sm:p-12 lg:p-24">
        <div className="w-full max-w-[320px] space-y-10">
          <div className="space-y-2">
            <h2 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
              Welcome back
            </h2>
            <p className="text-sm font-light text-zinc-500 dark:text-zinc-400">
              Please enter your details to sign in.
            </p>
          </div>

          <LoginForm />

          <p className="px-8 text-center text-[10px] leading-relaxed text-zinc-400 dark:text-zinc-600">
            By clicking login, you agree to our{' '}
            <a
              href="#"
              className="underline underline-offset-2 transition-colors hover:text-zinc-900 dark:hover:text-zinc-50"
            >
              Terms
            </a>{' '}
            and{' '}
            <a
              href="#"
              className="underline underline-offset-2 transition-colors hover:text-zinc-900 dark:hover:text-zinc-50"
            >
              Privacy Policy
            </a>
            .
          </p>
        </div>
      </div>
    </div>
  )
}
