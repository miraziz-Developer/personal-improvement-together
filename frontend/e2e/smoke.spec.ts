import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

// The main paths of the app, end to end: language, the daily routine, adding a challenge
// into it, the wizard's checks, and pausing a challenge.
const API = process.env.E2E_API_URL ?? "http://localhost:8000/api/v1";

// Registration is rate limited (5 an hour per IP), so the whole run shares one user.
let shared: Promise<string> | null = null;
const user = (request: APIRequestContext) => (shared ??= register(request));

async function register(request: APIRequestContext): Promise<string> {
  const regions = await (await request.get(`${API}/regions`)).json();
  const suffix = Math.random().toString(36).slice(2, 8);
  const response = await request.post(`${API}/auth/register`, {
    data: {
      username: `e2e_${suffix}`,
      password: `e2e-parol-${suffix}-${Date.now()}`,
      birth_date: "2003-01-01",
      region_id: regions[0].id,
      accepted_terms_version: "2026-09-25",
    },
  });
  expect(response.ok()).toBeTruthy();
  return (await response.json()).access_token;
}

async function signIn(page: Page, token: string) {
  await page.addInitScript((value) => {
    localStorage.setItem("pit.token", value);
    localStorage.setItem("pit.locale", "uz");
  }, token);
}

async function catalogId(request: APIRequestContext, durationDays: number): Promise<string> {
  const catalog = await (await request.get(`${API}/challenges`)).json();
  return catalog.find((c: { duration_days: number }) => c.duration_days === durationDays).id;
}

test("the landing speaks both languages", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("va'dangni");
  await page.getByRole("button", { name: "ru", exact: true }).first().click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Сдержи");
});

test("a challenge goes straight into the routine at the chosen time", async ({ page, request }) => {
  await signIn(page, await user(request));
  await page.goto("/routine");
  await page.getByRole("button", { name: "Challenge qo'shish" }).first().click();
  await page.getByText("14 kun ichki xotirjamlik").click();
  await page.getByLabel("Boshlanish vaqti").fill("21:00");
  await page.getByRole("button", { name: "Kun tartibiga qo'shish" }).click();
  await expect(page.getByText("10 daqiqa meditatsiya")).toBeVisible();
  await expect(page.getByText("21:00").first()).toBeVisible();
});

test("the wizard waits until a commitment is described", async ({ page, request }) => {
  await signIn(page, await user(request));
  await page.goto("/routine/new");
  await page.getByPlaceholder("Masalan: 3 oyda backend dasturchi bo'lish").fill("Har kuni sport bilan shug'ullanish");
  // A user already on challenges gets one more step ("when do you do them?") first.
  const other = page.getByRole("button", { name: "+ Boshqa" });
  for (let step = 0; step < 3 && !(await other.isVisible()); step++) {
    await page.getByRole("button", { name: "Keyingisi" }).click();
    await page.waitForTimeout(400);
  }
  await other.click();
  const next = page.getByRole("button", { name: "Keyingisi" });
  await expect(next).toBeDisabled();
  await page.getByPlaceholder("Nima qilasiz? Masalan: yo'l, sport zali").fill("Yo'l");
  await expect(next).toBeEnabled();
});

test("a free challenge can be paused", async ({ page, request }) => {
  const token = await user(request);
  const joined = await request.post(`${API}/challenges/${await catalogId(request, 30)}/join`, {
    data: { mode: "free" },
    headers: { Authorization: `Bearer ${token}` },
  });
  const { id } = await joined.json();
  await signIn(page, token);
  await page.goto(`/c/${id}`);
  await page.getByRole("button", { name: "Pauza qilish" }).first().click();
  await page.getByRole("button", { name: "2 kun" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Pauza qilish" }).click();
  await expect(page.getByText(/Pauza: .* 2 kun/)).toBeVisible();
});
