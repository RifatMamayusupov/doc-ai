/** @type {import('next').NextConfig} */
const nextConfig = {
    // Use Babel instead of SWC if SWC fails
    swcMinify: false,

    // Environment variables
    env: {
        NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
        NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
    },

    // Ignore TypeScript errors during build (for development)
    typescript: {
        ignoreBuildErrors: true,
    },

    // Ignore ESLint errors during build
    eslint: {
        ignoreDuringBuilds: true,
    },

    // Experimental features
    experimental: {
        forceSwcTransforms: false,
    },
}

module.exports = nextConfig
