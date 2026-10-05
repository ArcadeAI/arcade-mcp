import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import { chromium } from "playwright";

const document = await readFile(new URL("../src/app_tools/editor.html", import.meta.url), "utf8");

async function openApp(options = {}) {
  const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL });
  const page = await browser.newPage();
  await page.setContent('<iframe title="Greeting App"></iframe>');
  await page.evaluate(({ html, options }) => {
    window.calls = [];
    window.opened = [];
    const tools = options.tools ?? ["AppTools_PreviewGreeting", "AppTools_UppercaseGreeting", "AppTools_GoogleProfile"];
    const frame = document.querySelector("iframe");
    window.notify = (method, params) => frame.contentWindow.postMessage({ jsonrpc: "2.0", method, params }, "*");
    window.addEventListener("message", (event) => {
      if (event.source !== frame.contentWindow || event.data?.id === undefined) return;
      const { id, method, params } = event.data;
      window.calls.push({ method, params });
      let result;
      let error;
      if (method === "ui/initialize") {
        result = { protocolVersion: "2026-01-26", hostInfo: { name: "test host", version: "1" }, hostCapabilities: { serverTools: {}, serverResources: {}, openLinks: {} }, hostContext: {} };
      } else if (method === "tools/list") {
        if (options.discoveryError) error = { code: options.discoveryError, message: "Discovery failed" };
        else result = { tools: tools.map((name) => ({ name, inputSchema: { type: "object" } })) };
      } else if (method === "resources/read") {
        const url = new URL(params.uri);
        result = { contents: [{ uri: params.uri, mimeType: "application/json", text: JSON.stringify({ version: 1, tools: url.searchParams.getAll("tool").filter((name) => tools.includes(name.replaceAll(".", "_"))).map((tool) => ({ tool, name: tool.replaceAll(".", "_") })) }) }] };
      } else if (method === "tools/call") {
        if (params.name === "AppTools_GoogleProfile" && !window.authorized) {
          result = { isError: true, content: [{ type: "text", text: JSON.stringify({ authorization_url: "https://accounts.example.com/authorize" }) }] };
        } else {
          const greeting = `Hello, ${params.arguments.name}!`;
          result = { content: [{ type: "text", text: params.name === "AppTools_UppercaseGreeting" ? greeting.toUpperCase() : greeting }] };
        }
      } else if (method === "ui/open-link") {
        window.opened.push(params.url);
        window.authorized = true;
        result = {};
      } else if (method === "ui/update-model-context") result = {};
      else error = { code: -32601, message: "Method not found" };
      if (options.discoveryDelay && method === "tools/list") {
        window.releaseDiscovery = () => frame.contentWindow.postMessage({ jsonrpc: "2.0", id, result, error }, "*");
      } else frame.contentWindow.postMessage({ jsonrpc: "2.0", id, result, error }, "*");
    });
    frame.srcdoc = html;
  }, { html: document, options });
  return { browser, page, app: page.frameLocator("iframe") };
}

test("the uppercase button calls another gateway tool with the edited name", async () => {
  const { browser, page, app } = await openApp();
  try {
    await app.locator("#name").fill("Grace");
    await app.locator("#uppercase").click({ timeout: 3000 });
    await app.locator("#result").filter({ hasText: "HELLO, GRACE!" }).waitFor();
    const call = await page.evaluate(() => window.calls.find(({ method }) => method === "tools/call"));
    assert.deepEqual(call.params, { name: "AppTools_UppercaseGreeting", arguments: { name: "Grace" } });
  } finally { await browser.close(); }
});
