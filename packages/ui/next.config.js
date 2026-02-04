/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Enable experimental features
  experimental: {
    serverActions: true,
  },
  // Environment variables
  env: {
    API_URL: process.env.API_URL || 'http://localhost:8001',
  },
};

module.exports = nextConfig;
