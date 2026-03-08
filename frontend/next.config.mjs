/** @type {import('next').NextConfig} */
const nextConfig = {
    output: "export",
    trailingSlash: true,
    async rewrites() {
        // rewrites only apply in dev mode (next dev); ignored in static export
        return [
            {
                source: "/api/:path*",
                destination: "http://localhost:8000/:path*",
            },
        ];
    },
};

export default nextConfig;
