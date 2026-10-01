// The site opened inside Telegram as a Mini App (https://core.telegram.org/bots/webapps).

export const TELEGRAM_SCRIPT = "https://telegram.org/js/telegram-web-app.js";

// The small part of Telegram.WebApp we use.
export type TelegramWebApp = {
  initData: string;
  ready(): void;
  expand(): void;
  setHeaderColor?(color: string): void;
  setBackgroundColor?(color: string): void;
  disableVerticalSwipes?(): void;
};

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

/** Telegram's app object when the page runs inside Telegram, otherwise null. */
export function telegramApp(): TelegramWebApp | null {
  if (typeof window === "undefined") return null;
  const app = window.Telegram?.WebApp;
  return app?.initData ? app : null;
}
