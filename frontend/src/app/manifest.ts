import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "PIT — Personal Improvement Together",
    short_name: "PIT",
    description: "Maqsadlarni har kungi odatga aylantiring: AI reja, isbot, murabbiy va do'stlar bilan.",
    lang: "uz",
    start_url: "/routine",
    scope: "/",
    display: "standalone",
    background_color: "#06060b",
    theme_color: "#06060b",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
