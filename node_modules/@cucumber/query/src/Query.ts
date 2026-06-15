import * as messages from '@cucumber/messages'
import {
  Attachment,
  Duration,
  Feature,
  GherkinDocument,
  Hook,
  Location,
  Meta,
  Pickle,
  PickleStep,
  Rule,
  Scenario,
  Step,
  StepDefinition,
  Suggestion,
  TestCase,
  TestCaseFinished,
  TestCaseStarted,
  TestRunFinished,
  TestRunHookFinished,
  TestRunHookStarted,
  TestRunStarted,
  TestStep,
  TestStepFinished,
  TestStepResult,
  TestStepResultStatus,
  TestStepStarted,
  TimeConversion,
  UndefinedParameterType,
} from '@cucumber/messages'
import { ArrayMultimap } from '@teppeis/multimaps'
import sortBy from 'lodash.sortby'

import { assert, statusOrdinal } from './helpers'
import { Lineage } from './Lineage'

export default class Query {
  private meta: Meta
  private testRunStarted: TestRunStarted
  private testRunFinished: TestRunFinished
  private readonly testCaseStartedById: Map<string, TestCaseStarted> = new Map()
  private readonly lineageById: Map<string, Lineage> = new Map()
  private readonly stepById: Map<string, Step> = new Map()
  private readonly pickleById: Map<string, Pickle> = new Map()
  private readonly pickleStepById: Map<string, PickleStep> = new Map()
  private readonly hookById: Map<string, Hook> = new Map()
  private readonly stepDefinitionById: Map<string, StepDefinition> = new Map()
  private readonly testCaseById: Map<string, TestCase> = new Map()
  private readonly testStepById: Map<string, TestStep> = new Map()
  private readonly testCaseFinishedByTestCaseStartedId: Map<string, TestCaseFinished> = new Map()
  private readonly testRunHookStartedById: Map<string, TestRunHookStarted> = new Map()
  private readonly testRunHookFinishedByTestRunHookStartedId: Map<string, TestRunHookFinished> =
    new Map()
  private readonly testStepStartedByTestCaseStartedId: ArrayMultimap<string, TestStepStarted> =
    new ArrayMultimap()
  private readonly testStepFinishedByTestCaseStartedId: ArrayMultimap<string, TestStepFinished> =
    new ArrayMultimap()
  private readonly attachmentsByTestCaseStartedId: ArrayMultimap<string, Attachment> =
    new ArrayMultimap()
  private readonly attachmentsByTestRunHookStartedId: ArrayMultimap<string, Attachment> =
    new ArrayMultimap()
  private readonly suggestionsByPickleStepId: ArrayMultimap<string, Suggestion> =
    new ArrayMultimap()
  private readonly undefinedParameterTypes: UndefinedParameterType[] = []

  public update(envelope: messages.Envelope) {
    if (envelope.meta) {
      this.meta = envelope.meta
    }
    if (envelope.gherkinDocument) {
      this.updateGherkinDocument(envelope.gherkinDocument)
    }
    if (envelope.pickle) {
      this.updatePickle(envelope.pickle)
    }
    if (envelope.hook) {
      this.hookById.set(envelope.hook.id, envelope.hook)
    }
    if (envelope.stepDefinition) {
      this.stepDefinitionById.set(envelope.stepDefinition.id, envelope.stepDefinition)
    }
    if (envelope.testRunStarted) {
      this.testRunStarted = envelope.testRunStarted
    }
    if (envelope.testRunHookStarted) {
      this.updateTestRunHookStarted(envelope.testRunHookStarted)
    }
    if (envelope.testRunHookFinished) {
      this.updateTestRunHookFinished(envelope.testRunHookFinished)
    }
    if (envelope.testCase) {
      this.updateTestCase(envelope.testCase)
    }
    if (envelope.testCaseStarted) {
      this.updateTestCaseStarted(envelope.testCaseStarted)
    }
    if (envelope.testStepStarted) {
      this.updateTestStepStarted(envelope.testStepStarted)
    }
    if (envelope.attachment) {
      this.updateAttachment(envelope.attachment)
    }
    if (envelope.testStepFinished) {
      this.updateTestStepFinished(envelope.testStepFinished)
    }
    if (envelope.testCaseFinished) {
      this.updateTestCaseFinished(envelope.testCaseFinished)
    }
    if (envelope.testRunFinished) {
      this.testRunFinished = envelope.testRunFinished
    }
    if (envelope.suggestion) {
      this.updateSuggestion(envelope.suggestion)
    }
    if (envelope.undefinedParameterType) {
      this.updateUndefinedParameterType(envelope.undefinedParameterType)
    }
  }

  private updateGherkinDocument(gherkinDocument: GherkinDocument) {
    if (gherkinDocument.feature) {
      this.updateFeature(gherkinDocument.feature, {
        gherkinDocument,
      })
    }
  }

  private updateFeature(feature: Feature, lineage: Lineage) {
    feature.children.forEach((featureChild) => {
      if (featureChild.background) {
        lineage.background = featureChild.background
        this.updateSteps(featureChild.background.steps)
      }
      if (featureChild.scenario) {
        this.updateScenario(featureChild.scenario, {
          ...lineage,
          feature,
        })
      }
      if (featureChild.rule) {
        this.updateRule(featureChild.rule, {
          ...lineage,
          feature,
        })
      }
    })
  }

  private updateRule(rule: Rule, lineage: Lineage) {
    rule.children.forEach((ruleChild) => {
      if (ruleChild.background) {
        lineage.ruleBackground = ruleChild.background
        this.updateSteps(ruleChild.background.steps)
      }
      if (ruleChild.scenario) {
        this.updateScenario(ruleChild.scenario, {
          ...lineage,
          rule,
        })
      }
    })
  }

  private updateScenario(scenario: Scenario, lineage: Lineage) {
    this.lineageById.set(scenario.id, {
      ...lineage,
      scenario,
    })
    scenario.examples.forEach((examples, examplesIndex) => {
      this.lineageById.set(examples.id, {
        ...lineage,
        scenario,
        examples,
        examplesIndex,
      })
      examples.tableBody.forEach((example, exampleIndex) => {
        this.lineageById.set(example.id, {
          ...lineage,
          scenario,
          examples,
          examplesIndex,
          example,
          exampleIndex,
        })
      })
    })
    this.updateSteps(scenario.steps)
  }

  private updateSteps(steps: ReadonlyArray<Step>) {
    steps.forEach((step) => this.stepById.set(step.id, step))
  }

  private updatePickle(pickle: Pickle) {
    this.pickleById.set(pickle.id, pickle)
    pickle.steps.forEach((pickleStep) => this.pickleStepById.set(pickleStep.id, pickleStep))
  }

  private updateTestRunHookStarted(testRunHookStarted: TestRunHookStarted) {
    this.testRunHookStartedById.set(testRunHookStarted.id, testRunHookStarted)
  }

  private updateTestRunHookFinished(testRunHookFinished: TestRunHookFinished) {
    this.testRunHookFinishedByTestRunHookStartedId.set(
      testRunHookFinished.testRunHookStartedId,
      testRunHookFinished
    )
  }

  private updateTestCase(testCase: TestCase) {
    this.testCaseById.set(testCase.id, testCase)
    testCase.testSteps.forEach((testStep) => {
      this.testStepById.set(testStep.id, testStep)
    })
  }

  private updateTestCaseStarted(testCaseStarted: TestCaseStarted) {
    this.testCaseStartedById.set(testCaseStarted.id, testCaseStarted)
  }

  private updateTestStepStarted(testStepStarted: TestStepStarted) {
    this.testStepStartedByTestCaseStartedId.put(testStepStarted.testCaseStartedId, testStepStarted)
  }

  private updateAttachment(attachment: Attachment) {
    if (attachment.testCaseStartedId) {
      this.attachmentsByTestCaseStartedId.put(attachment.testCaseStartedId, attachment)
    }
    if (attachment.testRunHookStartedId) {
      this.attachmentsByTestRunHookStartedId.put(attachment.testRunHookStartedId, attachment)
    }
  }

  private updateTestStepFinished(testStepFinished: TestStepFinished) {
    this.testStepFinishedByTestCaseStartedId.put(
      testStepFinished.testCaseStartedId,
      testStepFinished
    )
  }

  private updateTestCaseFinished(testCaseFinished: TestCaseFinished) {
    this.testCaseFinishedByTestCaseStartedId.set(
      testCaseFinished.testCaseStartedId,
      testCaseFinished
    )
  }

  private updateSuggestion(suggestion: Suggestion) {
    this.suggestionsByPickleStepId.put(suggestion.pickleStepId, suggestion)
  }

  private updateUndefinedParameterType(undefinedParameterType: UndefinedParameterType) {
    this.undefinedParameterTypes.push(undefinedParameterType)
  }

  public countMostSevereTestStepResultStatus(): Record<TestStepResultStatus, number> {
    const result: Record<TestStepResultStatus, number> = {
      [TestStepResultStatus.AMBIGUOUS]: 0,
      [TestStepResultStatus.FAILED]: 0,
      [TestStepResultStatus.PASSED]: 0,
      [TestStepResultStatus.PENDING]: 0,
      [TestStepResultStatus.SKIPPED]: 0,
      [TestStepResultStatus.UNDEFINED]: 0,
      [TestStepResultStatus.UNKNOWN]: 0,
    }
    for (const testCaseStarted of this.findAllTestCaseStarted()) {
      const mostSevereResult = sortBy(
        this.findTestStepFinishedAndTestStepBy(testCaseStarted).map(
          ([testStepFinished]) => testStepFinished.testStepResult
        ),
        [(testStepResult) => statusOrdinal(testStepResult.status)]
      ).at(-1)
      if (mostSevereResult) {
        result[mostSevereResult.status]++
      }
    }
    return result
  }

  public countTestCasesStarted(): number {
    return this.findAllTestCaseStarted().length
  }

  public findAllPickles(): ReadonlyArray<Pickle> {
    return [...this.pickleById.values()]
  }

  public findAllPickleSteps(): ReadonlyArray<PickleStep> {
    return [...this.pickleStepById.values()]
  }

  public findAllStepDefinitions(): ReadonlyArray<StepDefinition> {
    return [...this.stepDefinitionById.values()]
  }

  public findAllTestCaseStarted(): ReadonlyArray<TestCaseStarted> {
    return sortBy(
      [...this.testCaseStartedById.values()].filter((testCaseStarted) => {
        const testCaseFinished = this.testCaseFinishedByTestCaseStartedId.get(testCaseStarted.id)
        // only include if not yet finished OR won't be retried
        return !testCaseFinished?.willBeRetried
      }),
      [
        (testCaseStarted) =>
          TimeConversion.timestampToMillisecondsSinceEpoch(testCaseStarted.timestamp),
        'id',
      ]
    )
  }

  public findAllTestCaseFinished(): ReadonlyArray<TestCaseFinished> {
    return sortBy(
      [...this.testCaseFinishedByTestCaseStartedId.values()].filter((testCaseFinished) => {
        // only include if not yet finished OR won't be retried
        return !testCaseFinished?.willBeRetried
      }),
      [
        (testCaseFinished) =>
          TimeConversion.timestampToMillisecondsSinceEpoch(testCaseFinished.timestamp),
        'id',
      ]
    )
  }

  public findAllTestCaseStartedOrderBy<T>(
    findOrderBy: (query: Query, testCaseStarted: TestCaseStarted) => T | undefined,
    order: (a: T, b: T) => number
  ): ReadonlyArray<TestCaseStarted> {
    const withOrderBy = this.findAllTestCaseStarted().map((testCaseStarted) => ({
      testCaseStarted,
      orderBy: findOrderBy(this, testCaseStarted),
    }))

    const sorted = withOrderBy.sort((a, b) => {
      if (a.orderBy === undefined && b.orderBy === undefined) return 0
      if (a.orderBy === undefined) return 1
      if (b.orderBy === undefined) return -1
      return order(a.orderBy, b.orderBy)
    })

    return sorted.map((item) => item.testCaseStarted)
  }

  public findAllTestCaseFinishedOrderBy<T>(
    findOrderBy: (query: Query, testCaseFinished: TestCaseFinished) => T | undefined,
    order: (a: T, b: T) => number
  ): ReadonlyArray<TestCaseFinished> {
    const withOrderBy = this.findAllTestCaseFinished().map((testCaseFinished) => ({
      testCaseFinished,
      orderBy: findOrderBy(this, testCaseFinished),
    }))

    const sorted = withOrderBy.sort((a, b) => {
      if (a.orderBy === undefined && b.orderBy === undefined) return 0
      if (a.orderBy === undefined) return 1
      if (b.orderBy === undefined) return -1
      return order(a.orderBy, b.orderBy)
    })

    return sorted.map((item) => item.testCaseFinished)
  }

  public findAllTestSteps(): ReadonlyArray<TestStep> {
    return [...this.testStepById.values()]
  }

  public findAllTestStepStarted(): ReadonlyArray<TestStepStarted> {
    return [...this.testStepStartedByTestCaseStartedId.values()]
  }

  public findAllTestStepFinished(): ReadonlyArray<TestStepFinished> {
    return [...this.testStepFinishedByTestCaseStartedId.values()]
  }

  public findAllTestRunHookStarted(): ReadonlyArray<TestRunHookStarted> {
    return [...this.testRunHookStartedById.values()]
  }

  public findAllTestRunHookFinished(): ReadonlyArray<TestRunHookFinished> {
    return [...this.testRunHookFinishedByTestRunHookStartedId.values()]
  }

  public findAllUndefinedParameterTypes(): ReadonlyArray<UndefinedParameterType> {
    return [...this.undefinedParameterTypes]
  }

  public findAttachmentsBy(
    element: TestStepFinished | TestRunHookFinished
  ): ReadonlyArray<Attachment> {
    if ('testStepId' in element) {
      return this.attachmentsByTestCaseStartedId
        .get(element.testCaseStartedId)
        .filter((attachment) => attachment.testStepId === element.testStepId)
    } else {
      return this.attachmentsByTestRunHookStartedId.get(element.testRunHookStartedId)
    }
  }

  public findHookBy(item: TestStep | TestRunHookStarted | TestRunHookFinished): Hook | undefined {
    if ('testRunHookStartedId' in item) {
      const testRunHookStarted = this.findTestRunHookStartedBy(item)
      assert.ok(testRunHookStarted, 'Expected to find TestRunHookStarted from TestRunHookFinished')
      return this.findHookBy(testRunHookStarted)
    }
    if (!item.hookId) {
      return undefined
    }
    return this.hookById.get(item.hookId)
  }

  public findMeta(): Meta | undefined {
    return this.meta
  }

  public findMostSevereTestStepResultBy(
    element: TestCaseStarted | TestCaseFinished
  ): TestStepResult | undefined {
    const testCaseStarted =
      'testCaseStartedId' in element ? this.findTestCaseStartedBy(element) : element
    return sortBy(
      this.findTestStepFinishedAndTestStepBy(testCaseStarted).map(
        ([testStepFinished]) => testStepFinished.testStepResult
      ),
      [(testStepResult) => statusOrdinal(testStepResult.status)]
    ).at(-1)
  }

  public findLocationOf(pickle: Pickle): Location | undefined {
    const lineage = this.findLineageBy(pickle)
    if (lineage?.example) {
      return lineage.example.location
    }
    return lineage?.scenario?.location
  }

  public findPickleBy(
    element: TestCaseStarted | TestCaseFinished | TestStepStarted
  ): Pickle | undefined {
    const testCase = this.findTestCaseBy(element)
    assert.ok(testCase, 'Expected to find TestCase from TestCaseStarted')
    return this.pickleById.get(testCase.pickleId)
  }

  public findPickleStepBy(testStep: TestStep): PickleStep | undefined {
    if (!testStep.pickleStepId) {
      return undefined
    }
    return this.pickleStepById.get(testStep.pickleStepId)
  }

  public findStepBy(pickleStep: PickleStep): Step | undefined {
    const [astNodeId] = pickleStep.astNodeIds
    assert.ok(astNodeId, 'Expected PickleStep to have an astNodeId')
    return this.stepById.get(astNodeId)
  }

  public findStepDefinitionsBy(testStep: TestStep): ReadonlyArray<StepDefinition> {
    return (testStep.stepDefinitionIds ?? []).map((id) => this.stepDefinitionById.get(id))
  }

  findSuggestionsBy(element: PickleStep | Pickle): ReadonlyArray<Suggestion> {
    if ('steps' in element) {
      return element.steps.flatMap((value) => this.findSuggestionsBy(value))
    }
    return this.suggestionsByPickleStepId.get(element.id)
  }

  public findUnambiguousStepDefinitionBy(testStep: TestStep): StepDefinition | undefined {
    if (testStep.stepDefinitionIds?.length === 1) {
      return this.stepDefinitionById.get(testStep.stepDefinitionIds[0])
    }
    return undefined
  }

  public findTestCaseBy(
    element: TestCaseStarted | TestCaseFinished | TestStepStarted | TestStepFinished
  ): TestCase | undefined {
    const testCaseStarted =
      'testCaseStartedId' in element ? this.findTestCaseStartedBy(element) : element
    assert.ok(testCaseStarted, 'Expected to find TestCaseStarted by TestStepStarted')
    return this.testCaseById.get(testCaseStarted.testCaseId)
  }

  public findTestCaseDurationBy(element: TestCaseStarted | TestCaseFinished): Duration | undefined {
    let testCaseStarted: TestCaseStarted
    let testCaseFinished: TestCaseFinished
    if ('testCaseStartedId' in element) {
      testCaseStarted = this.findTestCaseStartedBy(element)
      testCaseFinished = element
    } else {
      testCaseStarted = element
      testCaseFinished = this.findTestCaseFinishedBy(element)
    }
    if (!testCaseFinished) {
      return undefined
    }
    return TimeConversion.millisecondsToDuration(
      TimeConversion.timestampToMillisecondsSinceEpoch(testCaseFinished.timestamp) -
        TimeConversion.timestampToMillisecondsSinceEpoch(testCaseStarted.timestamp)
    )
  }

  public findTestCaseStartedBy(
    element: TestCaseFinished | TestStepStarted | TestStepFinished
  ): TestCaseStarted | undefined {
    return this.testCaseStartedById.get(element.testCaseStartedId)
  }

  public findTestCaseFinishedBy(testCaseStarted: TestCaseStarted): TestCaseFinished | undefined {
    return this.testCaseFinishedByTestCaseStartedId.get(testCaseStarted.id)
  }

  public findTestRunHookStartedBy(
    testRunHookFinished: TestRunHookFinished
  ): TestRunHookStarted | undefined {
    return this.testRunHookStartedById.get(testRunHookFinished.testRunHookStartedId)
  }

  public findTestRunHookFinishedBy(
    testRunHookStarted: TestRunHookStarted
  ): TestRunHookFinished | undefined {
    return this.testRunHookFinishedByTestRunHookStartedId.get(testRunHookStarted.id)
  }

  public findTestRunDuration(): Duration | undefined {
    if (!this.testRunStarted || !this.testRunFinished) {
      return undefined
    }
    return TimeConversion.millisecondsToDuration(
      TimeConversion.timestampToMillisecondsSinceEpoch(this.testRunFinished.timestamp) -
        TimeConversion.timestampToMillisecondsSinceEpoch(this.testRunStarted.timestamp)
    )
  }

  public findTestRunFinished(): TestRunFinished | undefined {
    return this.testRunFinished
  }

  public findTestRunStarted(): TestRunStarted | undefined {
    return this.testRunStarted
  }

  public findTestStepBy(element: TestStepStarted | TestStepFinished): TestStep | undefined {
    return this.testStepById.get(element.testStepId)
  }

  public findTestStepsStartedBy(
    element: TestCaseStarted | TestCaseFinished
  ): ReadonlyArray<TestStepStarted> {
    const testCaseStartedId =
      'testCaseStartedId' in element ? element.testCaseStartedId : element.id
    // multimaps `get` implements `getOrDefault([])` behaviour internally
    return [...this.testStepStartedByTestCaseStartedId.get(testCaseStartedId)]
  }

  public findTestStepsFinishedBy(
    element: TestCaseStarted | TestCaseFinished
  ): ReadonlyArray<TestStepFinished> {
    const testCaseStarted =
      'testCaseStartedId' in element ? this.findTestCaseStartedBy(element) : element
    // multimaps `get` implements `getOrDefault([])` behaviour internally
    return [...this.testStepFinishedByTestCaseStartedId.get(testCaseStarted.id)]
  }

  public findTestStepFinishedAndTestStepBy(
    testCaseStarted: TestCaseStarted
  ): ReadonlyArray<[TestStepFinished, TestStep]> {
    return this.testStepFinishedByTestCaseStartedId
      .get(testCaseStarted.id)
      .map((testStepFinished) => {
        const testStep = this.findTestStepBy(testStepFinished)
        assert.ok(testStep, 'Expected to find TestStep by TestStepFinished')
        return [testStepFinished, testStep]
      })
  }

  public findLineageBy(element: Pickle | TestCaseStarted | TestCaseFinished): Lineage | undefined {
    const pickle = 'astNodeIds' in element ? element : this.findPickleBy(element)
    const deepestAstNodeId = pickle.astNodeIds.at(-1)
    assert.ok(deepestAstNodeId, 'Expected Pickle to have at least one astNodeId')
    return this.lineageById.get(deepestAstNodeId)
  }
}
