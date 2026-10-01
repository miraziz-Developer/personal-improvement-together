"use client";

import { useRouter } from "next/navigation";
import Script from "next/script";
import { useEffect, useRef, useState } from "react";

import { OrDivider } from "@/components/AuthFields";
import { useToast } from "@/components/toast";
import { api, errorMessage } from "@/lib/api";
import { useAuth, useFeatures } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";

export const GOOGLE_SIGNUP_KEY = "pit.google-signup";

// The same "finish your profile" step serves a new Google account and a new Telegram user.
export type GoogleSignup = { token: string; email: string | null; username: string; next: string; provider?: "google" | "telegram" };

type GoogleOut = {
  access_token: string | null;
  signup_token: string | null;
  email: string | null;
  suggested_username: string | null;
};

// The small part of Google Identity Services we use (https://accounts.google.com/gsi/client).
type GoogleIdentityServices = {
  accounts: {
    id: {
      initialize(options: { client_id: string; callback: (response: { credential: string }) => void }): void;
      renderButton(parent: HTMLElement, options: Record<string, string | number>): void;
    };
  };
};

declare global {
  interface Window {
    google?: GoogleIdentityServices;
  }
}

/** "Continue with Google". Known accounts sign in; new ones go on to finish their profile. */
export function GoogleButton({ next = "/routine" }: { next?: string }) {
  const { googleClientId } = useFeatures();
  const { signIn } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const slot = useRef<HTMLDivElement>(null);
  const [loaded, setLoaded] = useState(false);
  const { locale } = useI18n();

  useEffect(() => {
    const google = window.google;
    if (!loaded || !googleClientId || !slot.current || !google) return;
    google.accounts.id.initialize({
      client_id: googleClientId,
      callback: async ({ credential }) => {
        try {
          const out = await api<GoogleOut>("/auth/google", { method: "POST", json: { credential } });
          if (out.access_token) {
            signIn(out.access_token);
            router.push(next);
            return;
          }
          const signup: GoogleSignup = { token: out.signup_token ?? "", email: out.email, username: out.suggested_username ?? "", next };
          sessionStorage.setItem(GOOGLE_SIGNUP_KEY, JSON.stringify(signup));
          router.push("/register/google");
        } catch (error) {
          toast("error", errorMessage(error));
        }
      },
    });
    slot.current.replaceChildren(); // switching language draws the button again
    google.accounts.id.renderButton(slot.current, {
      theme: "filled_black",
      size: "large",
      shape: "pill",
      text: "continue_with",
      locale,
      width: Math.min(slot.current.offsetWidth, 400),
    });
  }, [loaded, googleClientId, signIn, router, toast, next, locale]);

  if (!googleClientId) return null;
  return (
    <>
      <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" onReady={() => setLoaded(true)} />
      {/* Google draws the button in a light-scheme iframe; on our dark page the browser would
          paint an opaque white box behind it unless the wrapper uses the same scheme. */}
      <div ref={slot} className="flex min-h-11 w-full justify-center [color-scheme:light]" />
      <OrDivider />
    </>
  );
}
