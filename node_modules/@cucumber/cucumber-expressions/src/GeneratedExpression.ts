import type ParameterType from './ParameterType.js'
import type { ParameterInfo } from './types.js'

export default class GeneratedExpression {
  constructor(
    private readonly expressionTemplate: string,
    public readonly parameterTypes: readonly ParameterType<unknown>[]
  ) {}

  get source() {
    return format(this.expressionTemplate, ...this.parameterTypes.map((t) => t.name || ''))
  }

  /**
   * Returns an array of parameter names to use in generated function/method signatures
   *
   * @returns {ReadonlyArray.<String>}
   */
  get parameterNames(): readonly string[] {
    return this.parameterInfos.map((i) => `${i.name}${i.count === 1 ? '' : i.count.toString()}`)
  }

  /**
   * Returns an array of ParameterInfo to use in generated function/method signatures
   */
  get parameterInfos(): readonly ParameterInfo[] {
    const usageByTypeName: { [key: string]: number } = {}
    return this.parameterTypes.map((t) => getParameterInfo(t, usageByTypeName))
  }
}

function getParameterInfo(
  parameterType: ParameterType<unknown>,
  usageByName: { [key: string]: number }
): ParameterInfo {
  const name = parameterType.name || ''
  let counter = usageByName[name]
  counter = counter ? counter + 1 : 1
  usageByName[name] = counter
  let type: string | null
  if (parameterType.type) {
    if (typeof parameterType.type === 'string') {
      type = parameterType.type
    } else if ('name' in parameterType.type) {
      type = parameterType.type.name
    } else {
      type = null
    }
  } else {
    type = null
  }
  return {
    type,
    name,
    count: counter,
  }
}

function format(pattern: string, ...args: readonly string[]): string {
  return pattern.replace(/{(\d+)}/g, (_match, number) => args[number])
}
