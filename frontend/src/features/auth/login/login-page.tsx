import { LoginForm } from '@/components/login-form'
import { LoginHero } from './login-hero'
import { RotatingTooltip } from '@/components/rotating-tooltip'

export function LoginPage() {
  return (
    <div className="flex min-h-screen w-full bg-gradient-to-br from-blue-50 via-cyan-50 to-blue-100">
      <LoginHero />

      {/* Right Side - Login Form */}
      <div className="flex flex-1 items-center justify-center p-8 sm:p-12 lg:p-24">
        <div className="w-full max-w-[380px] space-y-10">
          <div className="space-y-3">
            <h2 className="text-3xl font-black bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">
              Welcome back
            </h2>
            <p className="text-base font-semibold text-blue-600">
              Please enter your details to sign in.
            </p>
          </div>

          <LoginForm />

          <RotatingTooltip />
        </div>
      </div>
    </div>
  )
}
