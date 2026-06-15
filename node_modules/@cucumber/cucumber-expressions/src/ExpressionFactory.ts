import CucumberExpression from './CucumberExpression.js'
import type ParameterTypeRegistry from './ParameterTypeRegistry.js'
import RegularExpression from './RegularExpression.js'
import type { Expression } from './types.js'

export default class ExpressionFactory {
  public constructor(private readonly parameterTypeRegistry: ParameterTypeRegistry) {}

  public createExpression(expression: string | RegExp): Expression {
    return typeof expression === 'string'
      ? new CucumberExpression(expression, this.parameterTypeRegistry)
      : new RegularExpression(expression, this.parameterTypeRegistry)
  }
}
