import type { NextConfig } from 'next';
import delivery from './delivery.config.json';

const nextConfig: NextConfig = {
  async rewrites() { return delivery.rewrites; },
  async headers() { return delivery.headers; },
};

export default nextConfig;
