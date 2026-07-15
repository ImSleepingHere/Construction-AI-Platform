import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Dynamic route pages (e.g. /projects/[id]) are force-dynamic and hit the
  // API on every load. Disable the client Router Cache for them so
  // client-side <Link>/router.push navigation between different ids always
  // fetches fresh, instead of risking a stale cached RSC payload (or a
  // stale not-found state) from a previously visited id in the same segment.
  experimental: {
    staleTimes: {
      dynamic: 0,
    },
  },
};

export default nextConfig;
