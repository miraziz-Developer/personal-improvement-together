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
  openTelegramLink?(url: string): void;
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

/** A t.me link that opens the bot with a start payload; the bot answers with a button into the app. */
export function botLink(bot: string, payload: string): string {
  return `https://t.me/${bot}?start=${payload}`;
}

/** Telegram's share sheet. Inside the Mini App a plain window.open of t.me is unreliable, so ask Telegram. */
export function shareToTelegram(url: string, text: string): void {
  const share = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`;
  const app = telegramApp();
  if (app?.openTelegramLink) app.openTelegramLink(share);
  else window.open(share, "_blank", "noopener");
}
