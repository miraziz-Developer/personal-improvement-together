import type { Metadata, Viewport } from "next";
import { Manrope, Unbounded } from "next/font/google";

import { Providers } from "./providers";
import "./globals.css";

const manrope = Manrope({ subsets: ["latin", "latin-ext", "cyrillic"], variable: "--font-manrope" });
const unbounded = Unbounded({ subsets: ["latin", "latin-ext"], variable: "--font-unbounded" });

export const metadata: Metadata = {
  title: "PIT — O'zingga bergan va'dangni bajar",
  description:
    "Maqsadlaringizni har kungi odatga aylantiring: AI reja, isbot, murabbiy va tengdoshlar bilan raqobat.",
};

export const viewport: Viewport = { themeColor: "#06060b" };

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="uz" className={`${manrope.variable} ${unbounded.variable}`}>
      <body className="font-sans">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
