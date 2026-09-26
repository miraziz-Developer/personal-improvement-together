"use client";

import { useEffect } from "react";

/** Registers /sw.js once per page load; the browser keeps it up to date. */
export function ServiceWorker() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js", { scope: "/", updateViaCache: "none" }).catch(() => {
      // Private mode or an old browser: the site works the same, just without push.
    });
  }, []);
  return null;
}
