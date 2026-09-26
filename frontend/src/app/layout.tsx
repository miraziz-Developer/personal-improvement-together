import type { Metadata, Viewport } from "next";
import { Manrope, Unbounded } from "next/font/google";

import { ServiceWorker } from "@/components/ServiceWorker";

import { Providers } from "./providers";
import "./globals.css";

const manrope = Manrope({ subsets: ["latin", "latin-ext", "cyrillic"], variable: "--font-manrope" });
const unbounded = Unbounded({ subsets: ["latin", "latin-ext"], variable: "--font-unbounded" });

export const metadata: Metadata = {
  title: "PIT — O'zingga bergan va'dangni bajar",
  description:
    "Maqsadlaringizni har kungi odatga aylantiring: AI reja, isbot, murabbiy va tengdoshlar bilan raqobat.",
  applicationName: "PIT",
  appleWebApp: { capable: true, title: "PIT", statusBarStyle: "black-translucent" },
  icons: { icon: "/icon-192.png", apple: "/apple-touch-icon.png" },
};

export const viewport: Viewport = { themeColor: "#06060b" };

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="uz" className={`${manrope.variable} ${unbounded.variable}`}>
      <body className="font-sans">
        <Providers>{children}</Providers>
        <ServiceWorker />
      </body>
    </html>
  );
}
