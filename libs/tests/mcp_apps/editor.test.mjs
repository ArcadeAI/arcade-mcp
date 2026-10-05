import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"
import { test } from "node:test"
import { chromium } from "playwright"

const document = await readFile(
    new URL(
        "../../../examples/mcp_servers/app_tools/src/app_tools/editor.html",
        import.meta.url
    ),
    "utf8"
)

async function openApp(options = {}) {
    const browser = await chromium.launch({
        headless: true,
        channel: process.env.PLAYWRIGHT_CHANNEL,
    })
    const page = await browser.newPage()
    await page.setContent('<iframe title="Greeting App"></iframe>')
    await page.evaluate(
        ({ html, options }) => {
            window.calls = []
            window.opened = []
            const tools = options.tools ?? [
                "AppTools_PreviewGreeting",
                "AppTools_UppercaseGreeting",
                "AppTools_GoogleProfile",
            ]
            const frame = document.querySelector("iframe")
            window.notify = (method, params) =>
                frame.contentWindow.postMessage(
                    { jsonrpc: "2.0", method, params },
                    "*"
                )
            window.addEventListener("message", (event) => {
                if (
                    event.source !== frame.contentWindow ||
                    event.data?.id === undefined
                )
                    return
                const { id, method, params } = event.data
                window.calls.push({ method, params })
                let result
                let error
                if (method === "ui/initialize") {
                    result = {
                        protocolVersion: "2026-01-26",
                        hostInfo: { name: "test host", version: "1" },
                        hostCapabilities: {
                            serverTools: {},
                            serverResources: {},
                            openLinks: {},
                        },
                        hostContext: {},
                    }
                } else if (method === "tools/list") {
                    if (options.discoveryError)
                        error = {
                            code: options.discoveryError,
                            message: "Discovery failed",
                        }
                    else {
                        const page = options.pages?.[params.cursor ? 1 : 0]
                        result = page ?? {
                            tools: tools.map((name) => ({
                                name,
                                inputSchema: { type: "object" },
                                _meta: options.visibility?.[name]
                                    ? {
                                          ui: {
                                              visibility:
                                                  options.visibility[name],
                                          },
                                      }
                                    : undefined,
                            })),
                        }
                    }
                } else if (method === "resources/read") {
                    const url = new URL(params.uri)
                    if (options.fallbackError)
                        error = {
                            code: -32603,
                            message: "Availability lookup failed",
                        }
                    else
                        result = {
                            contents: [
                                {
                                    uri: options.invalidFallback
                                        ? "wrong-uri"
                                        : params.uri,
                                    mimeType: "application/json",
                                    text: JSON.stringify({
                                        version: 1,
                                        tools: url.searchParams
                                            .getAll("tool")
                                            .filter((name) =>
                                                tools.includes(
                                                    name.replaceAll(".", "_")
                                                )
                                            )
                                            .map((tool) => ({
                                                tool,
                                                name: tool.replaceAll(".", "_"),
                                            })),
                                    }),
                                },
                            ],
                        }
                } else if (method === "tools/call") {
                    if (
                        params.name === "AppTools_GoogleProfile" &&
                        !window.authorized
                    ) {
                        if (options.urlElicitation)
                            error = {
                                code: -32042,
                                message: "Authorization required",
                                data: {
                                    elicitations: [
                                        {
                                            url: "https://accounts.example.com/authorize",
                                            elicitationId: "auth-1",
                                            mode: "url",
                                            message: "Authorize Google",
                                        },
                                    ],
                                },
                            }
                        else
                            result = {
                                isError: true,
                                content: [
                                    {
                                        type: "text",
                                        text: JSON.stringify({
                                            authorization_url:
                                                "https://accounts.example.com/authorize",
                                        }),
                                    },
                                ],
                            }
                    } else {
                        const greeting = `Hello, ${params.arguments.name}!`
                        result = {
                            content: [
                                {
                                    type: "text",
                                    text:
                                        params.name ===
                                        "AppTools_UppercaseGreeting"
                                            ? greeting.toUpperCase()
                                            : greeting,
                                },
                            ],
                        }
                    }
                } else if (method === "ui/open-link") {
                    window.opened.push(params.url)
                    window.authorized = true
                    result = {}
                } else if (method === "ui/update-model-context") result = {}
                else error = { code: -32601, message: "Method not found" }
                if (options.discoveryDelay && method === "tools/list") {
                    window.releaseDiscovery = () =>
                        frame.contentWindow.postMessage(
                            { jsonrpc: "2.0", id, result, error },
                            "*"
                        )
                } else
                    frame.contentWindow.postMessage(
                        { jsonrpc: "2.0", id, result, error },
                        "*"
                    )
            })
            frame.srcdoc = html
        },
        { html: document, options }
    )
    return { browser, page, app: page.frameLocator("iframe") }
}

test("the uppercase button calls another gateway tool with the edited name", async () => {
    const { browser, page, app } = await openApp()
    try {
        await app.locator("#name").fill("Grace")
        await app.locator("#uppercase").click({ timeout: 3000 })
        await app
            .locator("#result")
            .filter({ hasText: "HELLO, GRACE!" })
            .waitFor()
        const call = await page.evaluate(() =>
            window.calls.find(({ method }) => method === "tools/call")
        )
        assert.deepEqual(call.params, {
            name: "AppTools_UppercaseGreeting",
            arguments: { name: "Grace" },
        })
    } finally {
        await browser.close()
    }
})

test("the preview button calls the original tool again", async () => {
    const { browser, page, app } = await openApp()
    try {
        await app.locator("#name").fill("Lin")
        await app.locator("#preview").click()
        await app
            .locator("#result")
            .filter({ hasText: "Hello, Lin!" })
            .waitFor()
        const calls = await page.evaluate(() =>
            window.calls.filter(({ method }) => method === "tools/call")
        )
        assert.deepEqual(calls[0].params, {
            name: "AppTools_PreviewGreeting",
            arguments: { name: "Lin" },
        })
    } finally {
        await browser.close()
    }
})

test("a missing secondary tool has no button, before the user edits", async () => {
    const { browser, app } = await openApp({
        tools: ["AppTools_PreviewGreeting"],
    })
    try {
        await app.locator("#name").fill("Lin")
        assert.equal(await app.locator("#uppercase").isVisible(), false)
        assert.equal(await app.locator("#profile").isVisible(), false)
        assert.equal(await app.locator("#preview").isEnabled(), true)
    } finally {
        await browser.close()
    }
})

test("pending discovery prevents editing or invoking an unverified action", async () => {
    const { browser, page, app } = await openApp({ discoveryDelay: true })
    try {
        await page.waitForFunction(() => !!window.releaseDiscovery)
        assert.equal(await app.locator("#name").isEnabled(), false)
        assert.equal(await app.locator("#uppercase").isEnabled(), false)
        await page.evaluate(() => window.releaseDiscovery())
        await app.locator("#name").fill("Grace")
    } finally {
        await browser.close()
    }
})

test("method-not-found uses the gateway fallback with a fresh request nonce", async () => {
    const { browser, page, app } = await openApp({ discoveryError: -32601 })
    try {
        await app.locator("#name").fill("Grace")
        await app.locator("#uppercase").click()
        await app
            .locator("#result")
            .filter({ hasText: "HELLO, GRACE!" })
            .waitFor()
        const reads = await page.evaluate(() =>
            window.calls.filter(({ method }) => method === "resources/read")
        )
        const uris = reads.map(({ params }) => new URL(params.uri))
        assert.equal(uris.length, 2)
        assert.equal(uris[0].origin, "null")
        assert.equal(uris[0].host, "gateway")
        assert.equal(uris[0].pathname, "/tool-availability/v1")
        assert.notEqual(
            uris[0].searchParams.get("request"),
            uris[1].searchParams.get("request")
        )
        assert.deepEqual(uris[0].searchParams.getAll("tool"), [
            "AppTools.PreviewGreeting",
            "AppTools.UppercaseGreeting",
            "AppTools.GoogleProfile",
        ])
    } finally {
        await browser.close()
    }
})

for (const options of [
    { discoveryError: -32603 },
    { discoveryError: -32601, fallbackError: true },
    { discoveryError: -32601, invalidFallback: true },
]) {
    test(`discovery failure leaves disabled controls, not a false missing-tool result: ${JSON.stringify(options)}`, async () => {
        const { browser, page, app } = await openApp(options)
        try {
            await app
                .locator("#status")
                .filter({ hasText: "Could not check tools" })
                .waitFor()
            assert.equal(await app.locator("#uppercase").isVisible(), true)
            assert.equal(await app.locator("#uppercase").isEnabled(), false)
            assert.equal(await app.locator("#refresh").isEnabled(), true)
            if (options.discoveryError === -32603)
                assert.equal(
                    await page.evaluate(() =>
                        window.calls.some(
                            ({ method }) => method === "resources/read"
                        )
                    ),
                    false
                )
        } finally {
            await browser.close()
        }
    })
}

test("native discovery follows pagination and honors app visibility", async () => {
    const { browser, page, app } = await openApp({
        pages: [
            {
                tools: [{ name: "AppTools_PreviewGreeting" }],
                nextCursor: "page-two",
            },
            {
                tools: [
                    { name: "AppTools_UppercaseGreeting" },
                    {
                        name: "AppTools_GoogleProfile",
                        _meta: { ui: { visibility: ["model"] } },
                    },
                ],
            },
        ],
    })
    try {
        await app.locator("#name").fill("Lin")
        assert.equal(await app.locator("#uppercase").isEnabled(), true)
        assert.equal(await app.locator("#profile").isVisible(), false)
        const calls = await page.evaluate(() =>
            window.calls.filter(({ method }) => method === "tools/list")
        )
        assert.deepEqual(
            calls.map(({ params }) => params),
            [{}, { cursor: "page-two" }]
        )
    } finally {
        await browser.close()
    }
})

test("an incomplete recommendation surface uses the fallback for other callable tools", async () => {
    const { browser, page, app } = await openApp({
        pages: [
            {
                tools: [
                    { name: "Arcade_SelectTools" },
                    { name: "AppTools_PreviewGreeting" },
                ],
            },
        ],
    })
    try {
        await app.locator("#name").fill("Grace")
        await app.locator("#uppercase").click()
        await app
            .locator("#result")
            .filter({ hasText: "HELLO, GRACE!" })
            .waitFor()
        assert.equal(
            await page.evaluate(
                () =>
                    window.calls.filter(
                        ({ method }) => method === "resources/read"
                    ).length
            ),
            2
        )
    } finally {
        await browser.close()
    }
})

test("a repeated pagination cursor is unknown, not a partial successful list", async () => {
    const { browser, app } = await openApp({
        pages: [
            {
                tools: [{ name: "AppTools_PreviewGreeting" }],
                nextCursor: "again",
            },
            { tools: [], nextCursor: "again" },
        ],
    })
    try {
        await app
            .locator("#status")
            .filter({ hasText: "Could not check tools" })
            .waitFor()
        assert.equal(await app.locator("#preview").isEnabled(), false)
    } finally {
        await browser.close()
    }
})

test("a message from the App itself cannot spoof a host tool result", async () => {
    const { browser, page, app } = await openApp()
    try {
        await app.locator("#name").fill("Grace")
        const iframe = page.frames()[1]
        const before = await app.locator("#result").textContent()
        await iframe.evaluate(
            () =>
                new Promise((resolve) => {
                    window.addEventListener(
                        "message",
                        function received(event) {
                            if (
                                event.data?.params?.content?.[0]?.text !==
                                "spoofed"
                            )
                                return
                            window.removeEventListener("message", received)
                            resolve()
                        }
                    )
                    window.postMessage(
                        {
                            jsonrpc: "2.0",
                            method: "ui/notifications/tool-result",
                            params: {
                                content: [{ type: "text", text: "spoofed" }],
                            },
                        },
                        "*"
                    )
                })
        )
        assert.equal(await app.locator("#result").textContent(), before)
        await app.locator("#uppercase").click()
        await app
            .locator("#result")
            .filter({ hasText: "HELLO, GRACE!" })
            .waitFor()
        assert.equal(await app.locator("#name").inputValue(), "Grace")
    } finally {
        await browser.close()
    }
})

for (const urlElicitation of [false, true]) {
    test(`authorization keeps edits and does not retry until asked (${urlElicitation ? "elicitation required" : "tool result"})`, async () => {
        const { browser, page, app } = await openApp({ urlElicitation })
        try {
            await app.locator("#name").fill("Grace")
            await app.locator("#profile").click()
            await app.locator("#authorization").waitFor()
            assert.equal(await app.locator("#name").inputValue(), "Grace")
            await app.locator("#authorize").click()
            await page.waitForFunction(() => window.opened.length === 1)
            assert.equal(
                await page.evaluate(
                    () =>
                        window.calls.filter(
                            ({ method }) => method === "tools/call"
                        ).length
                ),
                1
            )
            await app.locator("#retry-action").click()
            await app
                .locator("#result")
                .filter({ hasText: "Hello, Grace!" })
                .waitFor()
            assert.equal(await app.locator("#authorization").isVisible(), false)
            const calls = await page.evaluate(() =>
                window.calls.filter(({ method }) => method === "tools/call")
            )
            assert.deepEqual(
                calls.map(({ params }) => params),
                Array(2).fill({
                    name: "AppTools_GoogleProfile",
                    arguments: { name: "Grace" },
                })
            )
        } finally {
            await browser.close()
        }
    })
}
