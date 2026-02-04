/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Environment variables
  env: {
    API_URL: process.env.API_URL || 'http://localhost:8001',
  },
};

module.exports = nextConfig;
