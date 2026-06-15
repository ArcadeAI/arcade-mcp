import CucumberExpressionError from './CucumberExpressionError.js'
import type Group from './Group.js'
import type ParameterType from './ParameterType.js'

export default class Argument {
  public static build(
    group: Group,
    parameterTypes: readonly ParameterType<unknown>[]
  ): readonly Argument[] {
    const argGroups = group.children || []

    if (argGroups.length !== parameterTypes.length) {
      throw new CucumberExpressionError(
        `Group has ${argGroups.length} capture groups (${argGroups.map(
          (g) => g.value
        )}), but there were ${parameterTypes.length} parameter types (${parameterTypes.map(
          (p) => p.name
        )})`
      )
    }

    return parameterTypes.map((parameterType, i) => new Argument(argGroups[i], parameterType))
  }

  constructor(
    public readonly group: Group,
    public readonly parameterType: ParameterType<unknown>
  ) {
    this.group = group
    this.parameterType = parameterType
  }

  /**
   * Get the value returned by the parameter type's transformer function.
   *
   * @param thisObj the object in which the transformer function is applied.
   */
  public getValue<T>(thisObj: unknown): T | null {
    const groupValues = this.group ? this.group.values : null
    return this.parameterType.transform(thisObj, groupValues)
  }

  public getParameterType() {
    return this.parameterType
  }
}
