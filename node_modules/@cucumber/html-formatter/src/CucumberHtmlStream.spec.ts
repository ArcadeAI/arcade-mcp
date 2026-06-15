import assert from 'node:assert'
import { Writable } from 'node:stream'
import type { Envelope } from '@cucumber/messages'

import { CucumberHtmlStream } from './CucumberHtmlStream'

async function renderAsHtml(...envelopes: Envelope[]): Promise<string> {
  return new Promise((resolve, reject) => {
    let html = ''
    const sink: Writable = new Writable({
      write(chunk: string, _: string, callback: (error?: Error | null) => void): void {
        html += chunk
        callback()
      },
    })
    sink.on('finish', () => resolve(html))
    const cucumberHtmlStream = new CucumberHtmlStream(
      `${__dirname}/dummy.css`,
      `${__dirname}/dummy.js`
    )
    cucumberHtmlStream.on('error', reject)
    cucumberHtmlStream.pipe(sink)

    for (const envelope of envelopes) {
      cucumberHtmlStream.write(envelope)
    }
    cucumberHtmlStream.end()
  })
}

describe('CucumberHtmlStream', () => {
  it('writes zero messages to html', async () => {
    const html = await renderAsHtml()
    assert(html.indexOf('window.CUCUMBER_MESSAGES = []') >= 0)
  })

  it('writes one message to html', async () => {
    const e1: Envelope = {
      testRunStarted: {
        timestamp: { seconds: 0, nanos: 0 },
      },
    }
    const html = await renderAsHtml(e1)
    assert(html.indexOf(`window.CUCUMBER_MESSAGES = [${JSON.stringify(e1)}]`) >= 0)
  })

  it('writes two messages to html', async () => {
    const e1: Envelope = {
      testRunStarted: {
        timestamp: { seconds: 0, nanos: 0 },
      },
    }
    const e2: Envelope = {
      testRunFinished: {
        timestamp: { seconds: 0, nanos: 0 },
        success: true,
      },
    }
    const html = await renderAsHtml(e1, e2)
    assert(
      html.indexOf(`window.CUCUMBER_MESSAGES = [${JSON.stringify(e1)},${JSON.stringify(e2)}]`) >= 0
    )
  })

  it('escapes forward slashes', async () => {
    const e1: Envelope = {
      gherkinDocument: {
        comments: [
          {
            location: {
              line: 0,
              column: 0,
            },
            text: `</script><script>alert('Hello')</script>`,
          },
        ],
      },
    }
    const html = await renderAsHtml(e1)
    assert(
      html.indexOf(
        `window.CUCUMBER_MESSAGES = [{"gherkinDocument":{"comments":[{"location":{"line":0,"column":0},"text":"\\x3C/script>\\x3Cscript>alert('Hello')\\x3C/script>"}]}}];`
      ) >= 0
    )
  })
})
