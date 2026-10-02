import { ImageResponse } from "next/og";

import { ShareCard } from "../card";
import { fetchShared } from "@/lib/share";

/** A tall picture for Instagram or Telegram stories: download it and post it. */
export async function GET(_request: Request, { params }: { params: Promise<{ token: string }> }) {
  const shared = await fetchShared((await params).token);
  if (!shared) return new Response("Not found", { status: 404 });
  return new ImageResponse(<ShareCard shared={shared} story />, {
    width: 1080,
    height: 1920,
    headers: { "Content-Disposition": `inline; filename="pit-${shared.username}.png"` },
  });
}
