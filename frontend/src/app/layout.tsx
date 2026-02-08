import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DemoForge",
  description: "Paste a URL. Get a product video.",
  openGraph: {
    title: "DemoForge",
    description: "Paste a URL. Get a product video.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="app">
          {/* Floating preview thumbnails - decorative */}
          <div className="floatingThumbnails" aria-hidden="true">
            <div className="floatingThumbnail" />
            <div className="floatingThumbnail" />
          </div>
          {children}
        </div>
      </body>
    </html>
  );
}
