/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    domains: ['localhost'],
  },
  // Allow all origins for development (mobile access)
  // Using a more targeted approach with explicit origins
  allowedDevOrigins: [
    // Localhost variants
    'http://localhost:3000',
    'http://localhost:3001',
    'http://localhost:3002',
    'http://localhost:3003',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:3001',
    'http://127.0.0.1:3002',
    'http://127.0.0.1:3003',
    // Your specific network IP from the error
    'http://192.168.0.130:3000',
    'http://192.168.0.130:3001',
    'http://192.168.0.130:3002',
    'http://192.168.0.130:3003',
    // Common home network ranges (192.168.x.x)
    'http://192.168.0.1:3000',
    'http://192.168.0.1:3001',
    'http://192.168.0.1:3002',
    'http://192.168.0.1:3003',
    'http://192.168.1.1:3000',
    'http://192.168.1.1:3001',
    'http://192.168.1.1:3002',
    'http://192.168.1.1:3003',
    // Add more as needed
  ],
  // Configure WebSocket and HMR for network access
  onDemandEntries: {
    maxInactiveAge: 25 * 1000,
    pagesBufferLength: 2,
  },
  // Allow WebSocket connections from any origin during development
  experimental: {
    // Disable WebSocket HMR when accessing via network to prevent connection errors
    ...(process.env.NODE_ENV === 'development' && {
      webpackBuildWorker: false,
    }),
  },
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
  webpack: (config, { dev, isServer }) => {
    if (dev && !isServer) {
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
      };
    }
    return config;
  },
};

module.exports = nextConfig;
