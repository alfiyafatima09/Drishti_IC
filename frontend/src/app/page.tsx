'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { FeatureCard } from '@/components/features/home/feature-card';
import { BarChart3, Upload, History, Smartphone } from 'lucide-react';
import { ROUTES } from '@/constants';

export default function HomePage() {
  const features = [
    {
      icon: BarChart3,
      title: 'Dashboard',
      description: 'Real-time monitoring and video feed',
      href: ROUTES.DASHBOARD,
      buttonText: 'Open Dashboard',
    },
    {
      icon: Upload,
      title: 'Scanner',
      description: 'Upload IC images for verification',
      href: ROUTES.SCANNER,
      buttonText: 'Scan IC',
    },
    {
      icon: Smartphone,
      title: 'Mobile Camera',
      description: 'Stream from mobile device',
      href: ROUTES.MOBILE,
      buttonText: 'Start Camera',
    },
    {
      icon: History,
      title: 'History',
      description: 'View past verification results',
      href: ROUTES.HISTORY,
      buttonText: 'View History',
    },
  ];

  const capabilities = [
    {
      title: 'AI-Powered Verification',
      description: 'Advanced machine learning models for counterfeit detection',
    },
    {
      title: 'Real-time Analysis',
      description: 'Live video streaming with instant verification results',
    },
    {
      title: 'Logo Detection',
      description: 'SIFT and CDS kernel-based logo matching',
    },
    {
      title: 'Font Analysis',
      description: 'Detect counterfeit components through font matching',
    },
  ];

  return (
    <div className="flex min-h-screen flex-col">
      <main className="flex-1">
        <div className="container mx-auto px-4 py-16">
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold mb-4">Drishti IC Verification System</h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Automated IC component verification and counterfeit detection using AI/ML
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
            {features.map((feature) => (
              <FeatureCard key={feature.title} {...feature} />
            ))}
          </div>

          <div className="mt-16 max-w-4xl mx-auto">
            <Card>
              <CardHeader>
                <CardTitle>Features</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {capabilities.map((capability) => (
                    <div key={capability.title}>
                      <h3 className="font-semibold mb-2">{capability.title}</h3>
                      <p className="text-sm text-muted-foreground">
                        {capability.description}
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}
