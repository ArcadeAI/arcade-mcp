import { NdjsonToMessageStream } from '@cucumber/message-streams'
import * as messages from '@cucumber/messages'
import assert from 'assert'
import fg from 'fast-glob'
import { convertWindowsPathToPattern } from 'fast-glob/out/utils/path'
import fs from 'fs'
import { pipeline,Writable } from 'stream'
import { promisify } from 'util'

import { GherkinDocumentWalker } from '../src'

const asyncPipeline = promisify(pipeline)

describe('Walking with messages', () => {
  const currentDir = convertWindowsPathToPattern(__dirname)
  const localMessageFiles = fg.sync(`${currentDir}/messages/**/*.ndjson`)
  const tckMessageFiles = fg.sync(
    `${currentDir}/../node_modules/@cucumber/compatibility-kit/features/**/*.ndjson`
  )
  const messageFiles = [].concat(localMessageFiles, tckMessageFiles)

  it('must have some messages for comparison', () => {
    assert.notEqual(messageFiles.length, 0)
  })

  for (const messageFile of messageFiles) {
    it(`can walk through GherkinDocuments in ${messageFile}`, async () => {
      const messageStream = new NdjsonToMessageStream()

      await asyncPipeline(
        fs.createReadStream(messageFile, 'utf-8'),
        messageStream,
        new Writable({
          objectMode: true,
          write(
            envelope: messages.Envelope,
            _encoding: string,
            callback: (error?: Error | null) => void
          ) {
            try {
              if (envelope.gherkinDocument) {
                const walker = new GherkinDocumentWalker()
                walker.walkGherkinDocument(envelope.gherkinDocument)
              }
              callback()
            } catch (error) {
              error.message += `\n${envelope.gherkinDocument.uri}\n`
              callback(error)
            }
          },
        })
      )
    }).timeout(30000)
  }
})
