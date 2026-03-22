import { test, expect } from "@playwright/test";

test.describe("App shell: Home, Portfolio, Research", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/v1/market/quote**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ticker: "AAPL",
          price: 190.25,
          change_percent: 1.2,
          change: 1.2,
          high: 191,
          low: 189,
          prev_close: 188,
          volume: 50_000_000,
          direction: "up",
          timestamp: new Date().toISOString(),
          market_open: true,
        }),
      });
    });
    await page.goto("/app/home");
    await expect(page.getByTestId("nav-home")).toBeVisible();
  });

  test("Home — stats, bottom bar, nav, Quick Trade", async ({ page }) => {
    await expect(page.getByText("PORTFOLIO VALUE", { exact: true }).first()).toBeVisible();
    await expect(
      page.locator("span.font-mono", { hasText: "Portfolio Value" }).first()
    ).toBeVisible();

    await page.route("**/api/v1/market/quote**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ticker: "AAPL",
          price: 190.25,
          change_percent: 1.2,
          change: 1.2,
          high: 191,
          low: 189,
          prev_close: 188,
          volume: 50_000_000,
          direction: "up",
          timestamp: new Date().toISOString(),
          market_open: true,
        }),
      });
    });

    await expect(page.getByText("QUICK TRADE", { exact: false })).toBeVisible();
    await expect(page.getByTestId("quicktrade-side-buy")).toBeVisible();
    await expect(page.getByTestId("quicktrade-side-sell")).toBeVisible();
    await page.getByTestId("quicktrade-side-sell").click();
    await page.getByTestId("quicktrade-ticker").fill("AAPL");
    await page.keyboard.press("Enter");
    await expect(page.getByText("$190.25", { exact: true }).first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("quicktrade-place-order")).toBeVisible();
    await expect(page.getByTestId("quicktrade-order-type")).toBeVisible();
    await page.getByTestId("quicktrade-side-buy").click();

    await page.getByTestId("nav-portfolio").click();
    await expect(page).toHaveURL(/\/app\/portfolio/);
    await page.getByTestId("nav-research").click();
    await expect(page).toHaveURL(/\/app\/research/);
    await page.getByTestId("nav-home").click();
    await expect(page).toHaveURL(/\/app\/home/);
  });

  test("Portfolio — summary and tables", async ({ page }) => {
    await page.getByTestId("nav-portfolio").click();
    await expect(page).toHaveURL(/\/app\/portfolio/);
    await expect(page.getByText("TOTAL VALUE", { exact: false })).toBeVisible();
    await expect(page.getByText("Active Positions", { exact: false })).toBeVisible();
    await expect(page.getByText("Trade History", { exact: false })).toBeVisible();
  });

  test("Research — example chip, typed query, mic button", async ({ page }) => {
    await page.getByTestId("nav-research").click();
    await expect(page.getByText("Ask anything about the markets", { exact: false })).toBeVisible();
    await page.getByTestId("research-example-2").click();
    await expect(page.getByText("What's Tesla trading at?", { exact: false })).toBeVisible({
      timeout: 5000,
    });
    await expect
      .poll(
        async () => {
          const body = page.locator("body");
          const t = await body.innerText();
          return /TSLA|Educational|price|MARKET_DATA|Could not complete/i.test(t);
        },
        { timeout: 60_000 }
      )
      .toBeTruthy();

    await page.getByTestId("research-input").fill("What is AAPL price?");
    await page.getByTestId("research-send").click();
    await expect
      .poll(
        async () => {
          const t = await page.locator("body").innerText();
          return /AAPL|Educational|price|Could not complete/i.test(t);
        },
        { timeout: 60_000 }
      )
      .toBeTruthy();

    await expect(page.getByTestId("research-mic")).toBeVisible();
    await page.getByTestId("research-mic").click();
    await page.waitForTimeout(400);
  });
});
