import {
  Background,
  Examples,
  Feature,
  GherkinDocument,
  Pickle,
  Rule,
  Scenario,
  TableRow,
} from '@cucumber/messages'

export interface Lineage {
  gherkinDocument?: GherkinDocument
  feature?: Feature
  background?: Background
  rule?: Rule
  ruleBackground?: Background
  scenario?: Scenario
  examples?: Examples
  examplesIndex?: number
  example?: TableRow
  exampleIndex?: number
}

export interface LineageReducer<T> {
  reduce: (lineage: Lineage, pickle: Pickle) => T
}

export type NamingStrategy = LineageReducer<string>

export enum NamingStrategyLength {
  LONG = 'LONG',
  SHORT = 'SHORT',
}

export enum NamingStrategyFeatureName {
  INCLUDE = 'INCLUDE',
  EXCLUDE = 'EXCLUDE',
}

export enum NamingStrategyExampleName {
  NUMBER = 'NUMBER',
  PICKLE = 'PICKLE',
  NUMBER_AND_PICKLE_IF_PARAMETERIZED = 'NUMBER_AND_PICKLE_IF_PARAMETERIZED',
}

class BuiltinNamingStrategy implements NamingStrategy {
  constructor(
    private readonly length: NamingStrategyLength,
    private readonly featureName: NamingStrategyFeatureName,
    private readonly exampleName: NamingStrategyExampleName
  ) {}

  reduce(lineage: Lineage, pickle: Pickle): string {
    const parts: string[] = []

    if (lineage.feature?.name && this.featureName === NamingStrategyFeatureName.INCLUDE) {
      parts.push(lineage.feature.name)
    }

    if (lineage.rule?.name) {
      parts.push(lineage.rule.name)
    }

    if (lineage.scenario?.name) {
      parts.push(lineage.scenario.name)
    } else {
      parts.push(pickle.name)
    }

    if (lineage.examples?.name) {
      parts.push(lineage.examples.name)
    }

    if (lineage.example) {
      const exampleNumber = [
        '#',
        (lineage.examplesIndex ?? 0) + 1,
        '.',
        (lineage.exampleIndex ?? 0) + 1,
      ].join('')

      switch (this.exampleName) {
        case NamingStrategyExampleName.NUMBER:
          parts.push(exampleNumber)
          break
        case NamingStrategyExampleName.NUMBER_AND_PICKLE_IF_PARAMETERIZED:
          if (lineage.scenario?.name !== pickle.name) {
            parts.push(exampleNumber + ': ' + pickle.name)
          } else {
            parts.push(exampleNumber)
          }
          break
        case NamingStrategyExampleName.PICKLE:
          parts.push(pickle.name)
          break
      }
    }

    if (this.length === NamingStrategyLength.SHORT) {
      return parts.at(-1) as string
    }
    return parts.filter((part) => !!part).join(' - ')
  }
}

export function namingStrategy(
  length: NamingStrategyLength,
  featureName: NamingStrategyFeatureName = NamingStrategyFeatureName.INCLUDE,
  exampleName: NamingStrategyExampleName = NamingStrategyExampleName.NUMBER_AND_PICKLE_IF_PARAMETERIZED
): NamingStrategy {
  return new BuiltinNamingStrategy(length, featureName, exampleName)
}
