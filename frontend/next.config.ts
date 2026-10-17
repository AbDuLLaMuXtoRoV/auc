import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // Showcase/demo uchun placeholder rasmlar. Prod'da haqiqiy media host qo'shiladi.
    remotePatterns: [{ protocol: "https", hostname: "picsum.photos" }],
  },
};

export default nextConfig;
