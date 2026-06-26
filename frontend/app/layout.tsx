import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  applicationName: "FarmWise",
  title: { default: "FarmWise", template: "%s — FarmWise" },
  description: "Satellite-based AI potato crop monitoring and verifiable production records",
  manifest: "/manifest.json",
  appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: "FarmWise" },
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  themeColor: "#0d1f15", width: "device-width", initialScale: 1, maximumScale: 1, viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400&display=swap" rel="stylesheet" />
      </head>
      <body style={{
        fontFamily: "'DM Sans', -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif",
        background: "#0d1f15",
        color: "#e8e6dc",
        WebkitFontSmoothing: "antialiased",
        overscrollBehavior: "none",
        minHeight: "100dvh",
        margin: 0,
      }}>
        {children}
      </body>
    </html>
  );
}
