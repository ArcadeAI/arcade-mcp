import assert from 'node:assert'
import fs from 'node:fs/promises'
import path from 'node:path'

import { Envelope, TestCaseStarted } from '@cucumber/messages'

import { Lineage } from './Lineage'
import Query from './Query'

describe('Query', () => {
  let cucumberQuery: Query
  beforeEach(() => {
    cucumberQuery = new Query()
  })

  describe('#findAllTestCaseStarted', () => {
    it('retains timestamp order', () => {
      const testCasesStarted: TestCaseStarted[] = [
        {
          id: '1',
          testCaseId: '1',
          attempt: 0,
          timestamp: {
            seconds: 1,
            nanos: 1,
          },
        },
        {
          id: '2',
          testCaseId: '2',
          attempt: 0,
          timestamp: {
            seconds: 2,
            nanos: 1,
          },
        },
        {
          id: '3',
          testCaseId: '3',
          attempt: 0,
          timestamp: {
            seconds: 2,
            nanos: 3,
          },
        },
      ]

      testCasesStarted
        .map((testCaseStarted) => ({ testCaseStarted }))
        .reverse()
        .forEach((envelope) => {
          cucumberQuery.update(envelope)
        })

      assert.deepStrictEqual(cucumberQuery.findAllTestCaseStarted(), testCasesStarted)
    })

    it('uses id as tie breaker', () => {
      const testCasesStarted: TestCaseStarted[] = [
        {
          id: '1',
          testCaseId: '1',
          attempt: 0,
          timestamp: {
            seconds: 1,
            nanos: 1,
          },
        },
        {
          id: '2',
          testCaseId: '2',
          attempt: 0,
          timestamp: {
            seconds: 1,
            nanos: 1,
          },
        },
      ]

      testCasesStarted
        .map((testCaseStarted) => ({ testCaseStarted }))
        .reverse()
        .forEach((envelope) => {
          cucumberQuery.update(envelope)
        })

      assert.deepStrictEqual(cucumberQuery.findAllTestCaseStarted(), testCasesStarted)
    })
  })

  describe('#findLineageBy', () => {
    it('returns correct lineage for a minimal scenario', async () => {
      const envelopes: ReadonlyArray<Envelope> = (
        await fs.readFile(path.join(__dirname, '../../testdata/src/minimal.ndjson'), {
          encoding: 'utf-8',
        })
      )
        .split('\n')
        .filter((line) => !!line)
        .map((line) => JSON.parse(line))
      envelopes.forEach((envelope) => cucumberQuery.update(envelope))

      const gherkinDocument = envelopes.find((envelope) => envelope.gherkinDocument).gherkinDocument
      const feature = gherkinDocument.feature
      const scenario = feature.children.find((child) => child.scenario).scenario
      const pickle = envelopes.find((envelope) => envelope.pickle).pickle

      assert.deepStrictEqual(cucumberQuery.findLineageBy(pickle), {
        gherkinDocument,
        feature,
        scenario,
      } satisfies Lineage)
    })

    it('returns correct lineage for a pickle from an examples table', async () => {
      const envelopes: ReadonlyArray<Envelope> = (
        await fs.readFile(path.join(__dirname, '../../testdata/src/examples-tables.ndjson'), {
          encoding: 'utf-8',
        })
      )
        .split('\n')
        .filter((line) => !!line)
        .map((line) => JSON.parse(line))
      envelopes.forEach((envelope) => cucumberQuery.update(envelope))

      const gherkinDocument = envelopes.find((envelope) => envelope.gherkinDocument).gherkinDocument
      const feature = gherkinDocument.feature
      const scenario = feature.children.find((child) => child.scenario).scenario
      const pickle = envelopes.find((envelope) => envelope.pickle).pickle
      const examples = scenario.examples[0]
      const example = examples.tableBody[0]

      assert.deepStrictEqual(cucumberQuery.findLineageBy(pickle), {
        gherkinDocument,
        feature,
        scenario,
        examples,
        examplesIndex: 0,
        example,
        exampleIndex: 0,
      } satisfies Lineage)
    })

    it('returns correct lineage for a pickle with background-derived steps', async () => {
      const envelopes: ReadonlyArray<Envelope> = (
        await fs.readFile(path.join(__dirname, '../../testdata/src/rules-backgrounds.ndjson'), {
          encoding: 'utf-8',
        })
      )
        .split('\n')
        .filter((line) => !!line)
        .map((line) => JSON.parse(line))
      envelopes.forEach((envelope) => cucumberQuery.update(envelope))

      const gherkinDocument = envelopes.find((envelope) => envelope.gherkinDocument).gherkinDocument
      const feature = gherkinDocument.feature
      const background = gherkinDocument.feature.children.find(
        (child) => child.background
      ).background
      const rule = feature.children.find((child) => child.rule).rule
      const ruleBackground = rule.children.find((child) => child.background).background
      const scenario = rule.children.find((child) => child.scenario).scenario
      const pickle = envelopes.find((envelope) => envelope.pickle).pickle

      assert.deepStrictEqual(cucumberQuery.findLineageBy(pickle), {
        gherkinDocument,
        feature,
        background,
        rule,
        ruleBackground,
        scenario,
      } satisfies Lineage)
    })
  })
})
