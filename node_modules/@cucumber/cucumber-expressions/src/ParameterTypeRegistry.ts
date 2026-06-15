import CucumberExpressionError from './CucumberExpressionError.js'
import CucumberExpressionGenerator from './CucumberExpressionGenerator.js'
import defineDefaultParameterTypes from './defineDefaultParameterTypes.js'
import { AmbiguousParameterTypeError } from './Errors.js'
import ParameterType from './ParameterType.js'
import type { DefinesParameterType } from './types.js'

export default class ParameterTypeRegistry implements DefinesParameterType {
  private readonly parameterTypeByName = new Map<string, ParameterType<unknown>>()
  private readonly parameterTypesByRegexp = new Map<string, Array<ParameterType<unknown>>>()

  constructor() {
    defineDefaultParameterTypes(this)
  }

  get parameterTypes(): IterableIterator<ParameterType<unknown>> {
    return this.parameterTypeByName.values()
  }

  public lookupByTypeName(typeName: string) {
    return this.parameterTypeByName.get(typeName)
  }

  public lookupByRegexp(
    parameterTypeRegexp: string,
    expressionRegexp: RegExp,
    text: string
  ): ParameterType<unknown> | undefined {
    const parameterTypes = this.parameterTypesByRegexp.get(parameterTypeRegexp)
    if (!parameterTypes) {
      return undefined
    }
    if (parameterTypes.length > 1 && !parameterTypes[0].preferForRegexpMatch) {
      // We don't do this check on insertion because we only want to restrict
      // ambiguity when we look up by Regexp. Users of CucumberExpression should
      // not be restricted.
      const generatedExpressions = new CucumberExpressionGenerator(
        () => this.parameterTypes
      ).generateExpressions(text)
      throw AmbiguousParameterTypeError.forRegExp(
        parameterTypeRegexp,
        expressionRegexp,
        parameterTypes,
        generatedExpressions
      )
    }
    return parameterTypes[0]
  }

  public defineParameterType(parameterType: ParameterType<unknown>) {
    if (parameterType.name !== undefined) {
      if (this.parameterTypeByName.has(parameterType.name)) {
        if (parameterType.name.length === 0) {
          throw new CucumberExpressionError(`The anonymous parameter type has already been defined`)
        } else {
          throw new CucumberExpressionError(
            `There is already a parameter type with name ${parameterType.name}`
          )
        }
      }
      this.parameterTypeByName.set(parameterType.name, parameterType)
    }

    for (const parameterTypeRegexp of parameterType.regexpStrings) {
      if (!this.parameterTypesByRegexp.has(parameterTypeRegexp)) {
        this.parameterTypesByRegexp.set(parameterTypeRegexp, [])
      }
      // biome-ignore lint/style/noNonNullAssertion: presence ensured above
      const parameterTypes = this.parameterTypesByRegexp.get(parameterTypeRegexp)!
      const existingParameterType = parameterTypes[0]
      if (
        parameterTypes.length > 0 &&
        existingParameterType.preferForRegexpMatch &&
        parameterType.preferForRegexpMatch
      ) {
        throw new CucumberExpressionError(
          'There can only be one preferential parameter type per regexp. ' +
            `The regexp /${parameterTypeRegexp}/ is used for two preferential parameter types, {${existingParameterType.name}} and {${parameterType.name}}`
        )
      }
      if (parameterTypes.indexOf(parameterType) === -1) {
        parameterTypes.push(parameterType)
        this.parameterTypesByRegexp.set(
          parameterTypeRegexp,
          parameterTypes.sort(ParameterType.compare)
        )
      }
    }
  }
}
