import type { Metadata } from 'next';
// Temporarily removed Google Fonts to debug CORS issue
// import { Inter } from 'next/font/google';
import './globals.css';
import { ThemeProvider } from '@/components/theme-provider';
import { Toaster } from '@/components/ui/toaster';
import { Navigation } from '@/components/navigation';

// const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Drishti IC Verification',
  description: 'AI-powered IC authenticity verification system',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              // Suppress WebSocket HMR errors when accessing via network IP
              (function() {
                if (typeof window !== 'undefined') {
                  // Suppress console errors for WebSocket HMR
                  const originalError = console.error;
                  const originalWarn = console.warn;
                  
                  console.error = function(...args) {
                    const message = args[0]?.toString() || '';
                    if (message.includes('WebSocket') || 
                        message.includes('webpack-hmr') ||
                        message.includes('cannot parse response') ||
                        message.includes('HMR')) {
                      return; // Suppress silently
                    }
                    originalError.apply(console, args);
                  };
                  
                  console.warn = function(...args) {
                    const message = args[0]?.toString() || '';
                    if (message.includes('WebSocket') ||
                        message.includes('webpack-hmr') ||
                        message.includes('HMR')) {
                      return; // Suppress silently
                    }
                    originalWarn.apply(console, args);
                  };

                  // Monitor for external requests (debugging CORS issues)
                  const originalFetch = window.fetch;
                  window.fetch = function(...args) {
                    const url = args[0]?.toString() || '';
                    if (url.includes('dudley-eds-88977.herokuapp.com') ||
                        url.includes('herokuapp.com')) {
                      console.error('🚨 EXTERNAL REQUEST DETECTED:', url);
                      console.trace('Stack trace:');
                      // Don't block, just log
                    }
                    return originalFetch.apply(this, args);
                  };

                  // Monitor XMLHttpRequest
                  const originalOpen = XMLHttpRequest.prototype.open;
                  XMLHttpRequest.prototype.open = function(method, url, ...args) {
                    if (url && (url.toString().includes('dudley-eds-88977.herokuapp.com') ||
                               url.toString().includes('herokuapp.com'))) {
                      console.error('🚨 XMLHTTP REQUEST DETECTED:', method, url);
                      console.trace('Stack trace:');
                    }
                    return originalOpen.apply(this, [method, url, ...args]);
                  };
                  
                  // Also suppress unhandled WebSocket errors
                  window.addEventListener('error', function(e) {
                    if (e.message && (
                      e.message.includes('WebSocket') ||
                      e.message.includes('webpack-hmr') ||
                      e.message.includes('cannot parse response')
                    )) {
                      e.preventDefault();
                      return false;
                    }
                  }, true);
                }
              })();
            `,
          }}
        />
      </head>
      <body className="font-sans">
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <Navigation />
          {children}
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
