import CombinatorialGeneratedExpressionFactory from './CombinatorialGeneratedExpressionFactory.js'
import type GeneratedExpression from './GeneratedExpression.js'
import ParameterType from './ParameterType.js'
import ParameterTypeMatcher from './ParameterTypeMatcher.js'

export default class CucumberExpressionGenerator {
  constructor(private readonly parameterTypes: () => Iterable<ParameterType<unknown>>) {}

  public generateExpressions(text: string): readonly GeneratedExpression[] {
    const parameterTypeCombinations: Array<Array<ParameterType<unknown>>> = []
    const parameterTypeMatchers = this.createParameterTypeMatchers(text)
    let expressionTemplate = ''
    let pos = 0
    let counter = 0

    while (true) {
      let matchingParameterTypeMatchers = []

      for (const parameterTypeMatcher of parameterTypeMatchers) {
        const advancedParameterTypeMatcher = parameterTypeMatcher.advanceTo(pos)
        if (advancedParameterTypeMatcher.find) {
          matchingParameterTypeMatchers.push(advancedParameterTypeMatcher)
        }
      }

      if (matchingParameterTypeMatchers.length > 0) {
        matchingParameterTypeMatchers = matchingParameterTypeMatchers.sort(
          ParameterTypeMatcher.compare
        )

        // Find all the best parameter type matchers, they are all candidates.
        const bestParameterTypeMatcher = matchingParameterTypeMatchers[0]
        const bestParameterTypeMatchers = matchingParameterTypeMatchers.filter(
          (m) => ParameterTypeMatcher.compare(m, bestParameterTypeMatcher) === 0
        )

        // Build a list of parameter types without duplicates. The reason there
        // might be duplicates is that some parameter types have more than one regexp,
        // which means multiple ParameterTypeMatcher objects will have a reference to the
        // same ParameterType.
        // We're sorting the list so preferential parameter types are listed first.
        // Users are most likely to want these, so they should be listed at the top.
        let parameterTypes = []
        for (const parameterTypeMatcher of bestParameterTypeMatchers) {
          if (parameterTypes.indexOf(parameterTypeMatcher.parameterType) === -1) {
            parameterTypes.push(parameterTypeMatcher.parameterType)
          }
        }
        parameterTypes = parameterTypes.sort(ParameterType.compare)

        parameterTypeCombinations.push(parameterTypes)

        expressionTemplate += escapeText(text.slice(pos, bestParameterTypeMatcher.start))
        expressionTemplate += `{{${counter++}}}`

        pos = bestParameterTypeMatcher.start + bestParameterTypeMatcher.group.length
      } else {
        break
      }

      if (pos >= text.length) {
        break
      }
    }

    expressionTemplate += escapeText(text.slice(pos))
    return new CombinatorialGeneratedExpressionFactory(
      expressionTemplate,
      parameterTypeCombinations
    ).generateExpressions()
  }

  private createParameterTypeMatchers(text: string): ParameterTypeMatcher[] {
    let parameterMatchers: ParameterTypeMatcher[] = []
    for (const parameterType of this.parameterTypes()) {
      if (parameterType.useForSnippets) {
        parameterMatchers = parameterMatchers.concat(
          CucumberExpressionGenerator.createParameterTypeMatchers2(parameterType, text)
        )
      }
    }
    return parameterMatchers
  }

  private static createParameterTypeMatchers2(
    parameterType: ParameterType<unknown>,
    text: string
  ): ParameterTypeMatcher[] {
    return parameterType.regexpStrings.map(
      (regexp) => new ParameterTypeMatcher(parameterType, regexp, text)
    )
  }
}

function escapeText(s: string): string {
  return s.replace(/\(/g, '\\(').replace(/{/g, '\\{').replace(/\//g, '\\/')
}
