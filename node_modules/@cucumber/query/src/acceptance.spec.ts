import assert from 'node:assert'
import fs from 'node:fs'
import * as path from 'node:path'
import { Writable } from 'node:stream'
import { pipeline } from 'node:stream/promises'

import { NdjsonToMessageStream } from '@cucumber/message-streams'
import { Envelope, Pickle } from '@cucumber/messages'

import Query from './Query'

const reversePickleComparator = (a: Pickle, b: Pickle): number => {
  if (a.uri !== b.uri) {
    return b.uri.localeCompare(a.uri)
  }
  if (a.location.line !== b.location.line) {
    return b.location.line - a.location.line
  }
  return b.location.column - a.location.column
}

describe('Acceptance Tests', async () => {
  const sources = [
    path.join(__dirname, '../../testdata/src/attachments.ndjson'),
    path.join(__dirname, '../../testdata/src/empty.ndjson'),
    path.join(__dirname, '../../testdata/src/global-hooks.ndjson'),
    path.join(__dirname, '../../testdata/src/global-hooks-attachments.ndjson'),
    path.join(__dirname, '../../testdata/src/hooks.ndjson'),
    path.join(__dirname, '../../testdata/src/minimal.ndjson'),
    path.join(__dirname, '../../testdata/src/rules.ndjson'),
    path.join(__dirname, '../../testdata/src/examples-tables.ndjson'),
    path.join(__dirname, '../../testdata/src/unknown-parameter-type.ndjson'),
  ]
  const queries: Queries = {
    countMostSevereTestStepResultStatus: (query: Query) =>
      query.countMostSevereTestStepResultStatus(),
    countTestCasesStarted: (query: Query) => query.countTestCasesStarted(),
    findAllPickles: (query: Query) => query.findAllPickles().length,
    findAllPickleSteps: (query: Query) => query.findAllPickleSteps().length,
    findAllStepDefinitions: (query: Query) => query.findAllStepDefinitions().length,
    findAllTestCaseStarted: (query: Query) => query.findAllTestCaseStarted().length,
    findAllTestCaseStartedOrderBy: (query: Query) =>
      query
        .findAllTestCaseStartedOrderBy(
          (q, testCaseStarted) => q.findPickleBy(testCaseStarted),
          reversePickleComparator
        )
        .map((testCaseStarted) => testCaseStarted.id),
    findAllTestCaseFinished: (query: Query) => query.findAllTestCaseFinished().length,
    findAllTestCaseFinishedOrderBy: (query: Query) =>
      query
        .findAllTestCaseFinishedOrderBy(
          (q, testCaseFinished) => q.findPickleBy(testCaseFinished),
          reversePickleComparator
        )
        .map((testCaseFinished) => testCaseFinished.testCaseStartedId),
    findAllTestRunHookStarted: (query: Query) => query.findAllTestRunHookStarted().length,
    findAllTestRunHookFinished: (query: Query) => query.findAllTestRunHookFinished().length,
    findTestRunHookStartedBy: (query: Query) =>
      query
        .findAllTestRunHookFinished()
        .map((testRunHookFinished) => query.findTestRunHookStartedBy(testRunHookFinished))
        .map((testRunHookStarted) => testRunHookStarted?.id),
    findTestRunHookFinishedBy: (query: Query) =>
      query
        .findAllTestRunHookStarted()
        .map((testRunHookStarted) => query.findTestRunHookFinishedBy(testRunHookStarted))
        .map((testRunHookFinished) => testRunHookFinished?.testRunHookStartedId),
    findAllTestSteps: (query: Query) => query.findAllTestSteps().length,
    findAttachmentsBy: (query: Query) => ({
      testStepFinished: query
        .findAllTestCaseStarted()
        .map((testCaseStarted) => query.findTestStepsFinishedBy(testCaseStarted))
        .map((testStepFinisheds) =>
          testStepFinisheds.map((testStepFinished) => query.findAttachmentsBy(testStepFinished))
        )
        .flat(2)
        .map((attachment) => [
          attachment.testStepId,
          attachment.testCaseStartedId,
          attachment.mediaType,
          attachment.contentEncoding,
        ]),
      testRunHookFinished: query
        .findAllTestRunHookFinished()
        .map((testRunHookFinished) => query.findAttachmentsBy(testRunHookFinished))
        .flat()
        .map((attachment) => [
          attachment.testRunHookStartedId,
          attachment.mediaType,
          attachment.contentEncoding,
        ]),
    }),

    findHookBy: (query: Query) => {
      return {
        testStep: query
          .findAllTestSteps()
          .map((testStep) => query.findHookBy(testStep))
          .map((hook) => hook?.id)
          .filter((value) => !!value),
        testRunHookStarted: query
          .findAllTestRunHookStarted()
          .map((testStep) => query.findHookBy(testStep))
          .map((hook) => hook?.id)
          .filter((value) => !!value),
        testRunHookFinished: query
          .findAllTestRunHookFinished()
          .map((testStep) => query.findHookBy(testStep))
          .map((hook) => hook?.id)
          .filter((value) => !!value),
      }
    },

    findMeta: (query: Query) => query.findMeta()?.implementation?.name,
    findMostSevereTestStepResultBy: (query: Query) => {
      return {
        testCaseStarted: query
          .findAllTestCaseStarted()
          .map((testCaseStarted) => query.findMostSevereTestStepResultBy(testCaseStarted))
          .map((testStepResult) => testStepResult?.status)
          .filter((value) => value),
        testCaseFinished: query
          .findAllTestCaseFinished()
          .map((testCaseStarted) => query.findMostSevereTestStepResultBy(testCaseStarted))
          .map((testStepResult) => testStepResult?.status)
          .filter((value) => value),
      }
    },
    findLocationOf: (query: Query) =>
      query.findAllPickles().map((pickle) => query.findLocationOf(pickle)),

    findPickleBy: (query: Query) => {
      return {
        testCaseStarted: query
          .findAllTestCaseStarted()
          .map((testCaseStarted) => query.findPickleBy(testCaseStarted))
          .map((pickle) => pickle?.name),
        testCaseFinished: query
          .findAllTestCaseFinished()
          .map((testCaseFinished) => query.findPickleBy(testCaseFinished))
          .map((pickle) => pickle?.name),
        testStepStarted: query
          .findAllTestStepFinished()
          .map((testCaseStarted) => query.findPickleBy(testCaseStarted))
          .map((pickle) => pickle?.name),
        testStepFinished: query
          .findAllTestStepFinished()
          .map((testCaseFinished) => query.findPickleBy(testCaseFinished))
          .map((pickle) => pickle?.name),
      }
    },
    findPickleStepBy: (query: Query) =>
      query
        .findAllTestSteps()
        .map((testStep) => query.findPickleStepBy(testStep))
        .map((pickleStep) => pickleStep?.text)
        .filter((value) => !!value),
    findStepBy: (query: Query) =>
      query
        .findAllPickleSteps()
        .map((pickleStep) => query.findStepBy(pickleStep))
        .map((step) => step?.text),
    findStepDefinitionsBy: (query: Query) =>
      query
        .findAllTestSteps()
        .map((pickleStep) =>
          query.findStepDefinitionsBy(pickleStep).map((stepDefinition) => stepDefinition?.id)
        ),
    findSuggestionsBy: (query: Query) => {
      return {
        pickleStep: query
          .findAllPickleSteps()
          .flatMap((pickleStep) => query.findSuggestionsBy(pickleStep))
          .map((suggestion) => suggestion.id),
        pickle: query
          .findAllPickles()
          .flatMap((pickle) => query.findSuggestionsBy(pickle))
          .map((suggestion) => suggestion.id),
      }
    },
    findUnambiguousStepDefinitionBy: (query: Query) =>
      query
        .findAllTestSteps()
        .map((pickleStep) => query.findUnambiguousStepDefinitionBy(pickleStep))
        .filter((stepDefinition) => !!stepDefinition)
        .map((stepDefinition) => stepDefinition.id),
    findTestCaseStartedBy: (query: Query) => {
      return {
        testCaseFinished: query
          .findAllTestCaseFinished()
          .map((testCaseFinished) => query.findTestCaseStartedBy(testCaseFinished))
          .map((testCase) => testCase?.id),
        testStepStarted: query
          .findAllTestStepStarted()
          .map((testStepStarted) => query.findTestCaseStartedBy(testStepStarted))
          .map((testCase) => testCase?.id),
        testStepFinished: query
          .findAllTestStepFinished()
          .map((testStepFinished) => query.findTestCaseStartedBy(testStepFinished))
          .map((testCase) => testCase?.id),
      }
    },
    findTestCaseBy: (query: Query) => {
      return {
        testCaseStarted: query
          .findAllTestCaseStarted()
          .map((testCaseStarted) => query.findTestCaseBy(testCaseStarted))
          .map((testCase) => testCase?.id),
        testCaseFinished: query
          .findAllTestCaseFinished()
          .map((testCaseFinished) => query.findTestCaseBy(testCaseFinished))
          .map((testCase) => testCase?.id),
        testStepStarted: query
          .findAllTestStepStarted()
          .map((testStepStarted) => query.findTestCaseBy(testStepStarted))
          .map((testCase) => testCase?.id),
        testStepFinished: query
          .findAllTestStepFinished()
          .map((testStepFinished) => query.findTestCaseBy(testStepFinished))
          .map((testCase) => testCase?.id),
      }
    },
    findTestCaseDurationBy: (query: Query) => {
      return {
        testCaseStarted: query
          .findAllTestCaseStarted()
          .map((testCaseStarted) => query.findTestCaseDurationBy(testCaseStarted)),
        testCaseFinished: query
          .findAllTestCaseFinished()
          .map((testCaseFinished) => query.findTestCaseDurationBy(testCaseFinished)),
      }
    },
    findTestCaseFinishedBy: (query: Query) =>
      query
        .findAllTestCaseStarted()
        .map((testCaseStarted) => query.findTestCaseFinishedBy(testCaseStarted))
        .map((testCaseFinished) => testCaseFinished?.testCaseStartedId),
    findTestRunDuration: (query: Query) => query.findTestRunDuration(),
    findTestRunFinished: (query: Query) => query.findTestRunFinished(),
    findTestRunStarted: (query: Query) => query.findTestRunStarted(),
    findTestStepBy: (query: Query) =>
      query
        .findAllTestCaseStarted()
        .flatMap((testCaseStarted) => query.findTestStepsStartedBy(testCaseStarted))
        .map((testStepStarted) => query.findTestStepBy(testStepStarted))
        .map((testStep) => testStep?.id),
    findTestStepsStartedBy: (query: Query) => {
      return {
        testCaseStarted: query
          .findAllTestCaseStarted()
          .map((testCaseStarted) => query.findTestStepsStartedBy(testCaseStarted))
          .map((testStepsStarted) =>
            testStepsStarted.map((testStepStarted) => testStepStarted.testStepId)
          ),
        testCaseFinished: query
          .findAllTestCaseFinished()
          .map((testCaseFinished) => query.findTestStepsStartedBy(testCaseFinished))
          .map((testStepsStarted) =>
            testStepsStarted.map((testStepStarted) => testStepStarted.testStepId)
          ),
      }
    },
    findTestStepByTestStepFinished: (query: Query) => {
      return {
        testCaseStarted: query
          .findAllTestCaseStarted()
          .flatMap((testCaseStarted) => query.findTestStepsFinishedBy(testCaseStarted))
          .map((testStepFinished) => query.findTestStepBy(testStepFinished))
          .map((testStep) => testStep?.id),
        testCaseFinished: query
          .findAllTestCaseFinished()
          .flatMap((testCaseFinished) => query.findTestStepsFinishedBy(testCaseFinished))
          .map((testStepFinished) => query.findTestStepBy(testStepFinished))
          .map((testStep) => testStep?.id),
      }
    },
    findTestStepsFinishedBy: (query: Query) =>
      query
        .findAllTestCaseStarted()
        .map((testCaseStarted) => query.findTestStepsFinishedBy(testCaseStarted))
        .map((testStepFinisheds) =>
          testStepFinisheds.map((testStepFinished) => testStepFinished?.testStepId)
        ),
    findTestStepFinishedAndTestStepBy: (query: Query) =>
      query
        .findAllTestCaseStarted()
        .flatMap((testCaseStarted) => query.findTestStepFinishedAndTestStepBy(testCaseStarted))
        .map(([testStepFinished, testStep]) => [testStepFinished.testStepId, testStep.id]),
    findAllUndefinedParameterTypes: (query: Query) =>
      query
        .findAllUndefinedParameterTypes()
        .map((undefinedParameterType) => [
          undefinedParameterType.name,
          undefinedParameterType.expression,
        ]),
  }

  for (const source of sources) {
    for (const methodName in queries) {
      const [suiteName] = path.basename(source).split('.')

      it(suiteName + ' -> ' + methodName, async () => {
        const query = new Query()

        await pipeline(
          fs.createReadStream(source, { encoding: 'utf-8' }),
          new NdjsonToMessageStream(),
          new Writable({
            objectMode: true,
            write(envelope: Envelope, _: BufferEncoding, callback) {
              query.update(envelope)
              callback()
            },
          })
        )

        const expectedResults = JSON.parse(
          fs.readFileSync(
            path.join(
              __dirname,
              '../../testdata/src/' + suiteName + '.' + methodName + '.results.json'
            ),
            {
              encoding: 'utf-8',
            }
          )
        )
        const actualResults = JSON.parse(JSON.stringify(queries[methodName](query)))
        assert.deepStrictEqual(actualResults, expectedResults)
      })
    }
  }
})

type Queries = {
  // eslint-disable-next-line @typescript-eslint/no-wrapper-object-types
  [key: string]: (query: Query) => Object
}
