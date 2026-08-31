import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";

const fixture = (name) =>
  JSON.parse(
    readFileSync(resolve("examples/papertrail-cartea/fixtures", name), "utf8"),
  );

test("Cartea preprint completes integrity, governed AI, and human review loops", async ({
  page,
}) => {
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));

  await page.route("**/api.crossref.org/works/**", (route) =>
    route.fulfill({ json: fixture("crossref.json") }),
  );
  await page.route("**/api.openalex.org/works/**", (route) =>
    route.fulfill({ json: fixture("openalex.json") }),
  );
  await page.route("**/esearch.fcgi?**", (route) =>
    route.fulfill({ json: fixture("pubmed-search.json") }),
  );

  await page.goto("/");
  await expect(page.locator("#report-input")).toHaveValue(
    /The Limited Virtue of Complexity/,
  );

  await page.locator("#language-select").selectOption("zh");
  await expect(page.getByRole("heading", { name: "人工审阅台" })).toBeVisible();
  await page.locator("#language-select").selectOption("en");

  await page.locator("#doi-input").fill("10.2139/ssrn.5202064");
  await page.locator("#doi-button").click();
  await expect(page.locator("#integrity-network")).toBeVisible();
  await expect(page.locator("#integrity-providers")).toContainText("crossref · ok");
  await expect(page.locator("#integrity-providers")).toContainText("openalex · ok");
  await expect(page.locator("#integrity-providers")).toContainText("pubmed · not_found");
  await expect(page.locator("#integrity-providers")).toContainText("crossmark · manual_required");
  await expect(page.locator("#integrity-graph")).toContainText("preprint");

  await page.locator("#draft-button").click();
  await expect(page.locator("#governed-review")).toBeVisible();
  const negativeControl = page
    .locator(".review-candidate")
    .filter({ hasText: "C002" });
  await expect(negativeControl).toContainText("possible contradiction");
  await expect(negativeControl).toContainText("possible overgeneralization");

  await page.locator("#review-claim").selectOption("C001");
  await page.locator("#review-source").selectOption("cartea2025");
  await page.locator("#review-verdict").selectOption("SUPPORTED");
  await page.locator("#review-quote").fill("Exact source text");
  await page.locator("#review-locator").fill("PDF page 43");
  await page.locator("#reviewer-id").fill("ai-assistant");
  await page.locator("#human-review-form").getByRole("button", { name: "Save human judgment" }).click();
  await expect(page.locator("#error")).toContainText("human reviewer ID is required");

  await page.locator("#review-claim").selectOption("C002");
  await page.locator("#review-source").selectOption("cartea2025");
  await page.locator("#review-verdict").selectOption("CONTRADICTED");
  await page
    .locator("#review-quote")
    .fill(
      "In fact, beyond a certain point, adding more features reduces out-of-sample prediction performance and portfolio Sharpe ratio.",
    );
  await page.locator("#review-locator").fill("PDF page 42, Section 5.3");
  await page.locator("#reviewer-id").fill("playwright-human-reviewer");
  await expect(page.locator("#review-ai-diff")).toContainText(
    "same direction",
  );
  await page.locator("#human-review-form").getByRole("button", { name: "Save human judgment" }).click();

  const saved = page.locator(".human-review-record").filter({ hasText: "C002" });
  await expect(saved).toContainText("Contradicted");
  let manifest = JSON.parse(await page.locator("#manifest-input").inputValue());
  expect(manifest.review_history).toHaveLength(1);
  expect(manifest.review_history[0].action).toBe("updated");
  expect(manifest.review_history[0].ai_recommendation.relation).toBe(
    "potential_contradiction",
  );

  await saved.getByRole("button", { name: "Edit" }).click();
  await page.locator("#review-note").fill("Synthetic browser acceptance review.");
  await page.locator("#human-review-form").getByRole("button", { name: "Save human judgment" }).click();
  manifest = JSON.parse(await page.locator("#manifest-input").inputValue());
  expect(manifest.review_history).toHaveLength(2);

  await saved.getByRole("button", { name: "Revoke" }).click();
  manifest = JSON.parse(await page.locator("#manifest-input").inputValue());
  expect(manifest.review_history).toHaveLength(3);
  expect(manifest.review_history[2].action).toBe("revoked");
  expect(consoleErrors).toEqual([]);
});
