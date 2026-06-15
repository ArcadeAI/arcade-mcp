import fs from 'node:fs'
import path from 'node:path'
import { pipeline } from 'node:stream/promises'

import { NdjsonToMessageStream } from '@cucumber/message-streams'
import { expect, test } from '@playwright/test'
import { sync } from 'glob'

import { CucumberHtmlStream } from '../src'

const fixtures = sync(`./node_modules/@cucumber/compatibility-kit/features/**/*.ndjson`)

test.beforeAll(async () => {
  const outputDir = path.join(__dirname, './__output__')

  for (const fixture of fixtures) {
    const name = path.basename(fixture, '.ndjson')
    const outputFile = path.join(outputDir, `${name}.html`)

    await pipeline(
      fs.createReadStream(fixture, { encoding: 'utf-8' }),
      new NdjsonToMessageStream(),
      new CucumberHtmlStream(
        path.join(__dirname, '../dist/main.css'),
        path.join(__dirname, '../dist/main.js'),
        path.join(__dirname, '../dist/src/icon.url')
      ),
      fs.createWriteStream(outputFile)
    )
  }
})

for (const fixture of fixtures) {
  const name = path.basename(fixture, '.ndjson')

  test(`can render ${name}`, async ({ page }) => {
    await page.goto(`/${name}.html`)
    await page.waitForSelector('#report', { timeout: 3000 })
    await expect(page).toHaveScreenshot(`${name}.png`, { fullPage: true })
  })
}
