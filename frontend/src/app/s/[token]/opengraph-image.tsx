import { ImageResponse } from "next/og";

import { ShareCard } from "./card";
import { fetchShared } from "@/lib/share";

export const alt = "PIT natijasi";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

/** The preview Telegram and other apps show under a shared link. */
export default async function Image({ params }: { params: Promise<{ token: string }> }) {
  const shared = await fetchShared((await params).token);
  if (!shared) {
    return new ImageResponse(<div style={{ display: "flex", width: "100%", height: "100%", background: "#0b0b14" }} />, size);
  }
  return new ImageResponse(<ShareCard shared={shared} story={false} />, size);
}
