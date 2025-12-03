import { LoginForm } from '@/components/login-form'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Shield, CheckCircle2, Sparkles } from 'lucide-react'

export function LoginPage() {
  return (
    <div className="bg-background flex min-h-screen">
      {/* Left Side - Beautiful Gradient with Project Information */}
      <div className="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-br from-blue-600 via-indigo-700 to-purple-800 p-8 lg:flex lg:w-1/2 lg:p-12">
        {/* Decorative gradient orbs */}
        <div className="absolute top-0 right-0 h-96 w-96 translate-x-1/2 -translate-y-1/2 rounded-full bg-blue-500/20 blur-3xl" />
        <div className="absolute bottom-0 left-0 h-96 w-96 -translate-x-1/2 translate-y-1/2 rounded-full bg-purple-500/20 blur-3xl" />
        <div className="bg-grid-white/10 absolute inset-0 [mask-image:linear-gradient(0deg,white,transparent)]" />

        <div className="relative z-10 space-y-8">
          {/* Header */}
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="rounded-xl border border-white/20 bg-white/10 p-3 shadow-lg backdrop-blur-sm">
                <Shield className="h-7 w-7 text-white" />
              </div>
              <h1 className="text-4xl font-bold tracking-tight text-white">Drishti IC</h1>
            </div>
            <p className="text-lg leading-relaxed font-medium text-white/90">
              Automated Optical Inspection (AOI) for Counterfeit IC Marking Detection
            </p>
          </div>

          <Separator className="bg-white/20" />

          {/* Project Info */}
          <div className="space-y-6">
            <div>
              <Badge className="mb-4 border-white/30 bg-white/20 text-white hover:bg-white/30">
                Smart India Hackathon 2025
              </Badge>
              <div className="space-y-2.5 text-sm">
                <p className="text-white/80">
                  <span className="font-semibold text-white">Problem ID:</span> 25162
                </p>
                <p className="text-white/80">
                  <span className="font-semibold text-white">Theme:</span> Smart Automation
                </p>
                <p className="text-white/80">
                  <span className="font-semibold text-white">Team:</span> Win Diesel
                </p>
                <p className="text-white/80">
                  <span className="font-semibold text-white">Category:</span> Software Edition
                </p>
              </div>
            </div>

            <div className="space-y-3">
              <p className="text-sm leading-relaxed text-white/90">
                <span className="font-semibold text-white">Drishti IC</span> is an AI-powered
                platform that automates the authentication and verification of Integrated Circuits
                (ICs). It integrates computer vision, optical character recognition (OCR), and OEM
                datasheet validation to identify counterfeit components in seconds.
              </p>
              <p className="border-l-2 border-white/30 pl-3 text-sm text-white/80 italic">
                "Drishti IC – India's Vision for Counterfeit-Free Electronics."
              </p>
            </div>
          </div>

          {/* Key Features */}
          <div className="space-y-4">
            <h3 className="flex items-center gap-2 text-lg font-semibold text-white">
              <Sparkles className="h-5 w-5 text-white" />
              Key Features
            </h3>
            <div className="grid gap-3">
              <div className="flex items-start gap-3 rounded-lg border border-white/10 bg-white/5 p-3 backdrop-blur-sm">
                <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-white" />
                <div>
                  <p className="text-sm font-medium text-white">AI-Based Optical Inspection</p>
                  <p className="text-xs text-white/70">
                    Automated inspection using object detection and OCR
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3 rounded-lg border border-white/10 bg-white/5 p-3 backdrop-blur-sm">
                <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-white" />
                <div>
                  <p className="text-sm font-medium text-white">OEM Datasheet Validation</p>
                  <p className="text-xs text-white/70">
                    Cross-verifies against official manufacturer standards
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3 rounded-lg border border-white/10 bg-white/5 p-3 backdrop-blur-sm">
                <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-white" />
                <div>
                  <p className="text-sm font-medium text-white">Real-Time Dashboard</p>
                  <p className="text-xs text-white/70">
                    Dynamic analytics with confidence scores and verdicts
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3 rounded-lg border border-white/10 bg-white/5 p-3 backdrop-blur-sm">
                <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-white" />
                <div>
                  <p className="text-sm font-medium text-white">Software-Only Deployment</p>
                  <p className="text-xs text-white/70">No specialized hardware required</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Stats */}
        <div className="relative z-10 space-y-4 border-t border-white/20 pt-6">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="rounded-lg border border-white/10 bg-white/5 p-3 backdrop-blur-sm">
              <div className="text-2xl font-bold text-white">80%</div>
              <div className="text-xs text-white/70">Faster</div>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/5 p-3 backdrop-blur-sm">
              <div className="text-2xl font-bold text-white">100%</div>
              <div className="text-xs text-white/70">Automated</div>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/5 p-3 backdrop-blur-sm">
              <div className="text-2xl font-bold text-white">24/7</div>
              <div className="text-xs text-white/70">Available</div>
            </div>
          </div>
          <p className="text-center text-xs text-white/60">
            © 2025 Team Win Diesel — All Rights Reserved
          </p>
        </div>
      </div>

      {/* Right Side - Login Form */}
      <div className="flex flex-1 items-center justify-center p-4 sm:p-6 lg:p-12">
        <div className="w-full max-w-md">
          <Card className="bg-card/50 border-0 p-6 shadow-xl backdrop-blur-sm sm:p-8">
            <div className="space-y-6">
              <div className="space-y-2 text-center">
                <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">Welcome Back</h2>
                <p className="text-muted-foreground text-sm sm:text-base">
                  Sign in to access Drishti IC platform
                </p>
              </div>
              <LoginForm />
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
