import type IToken from './IToken'
import type { RuleType, TokenType } from './Parser'

export default class AstNode {
  // biome-ignore lint/suspicious/noExplicitAny: keys and values are heterogeneous AST entries
  private readonly subItems = new Map<any, any[]>()

  constructor(public readonly ruleType: RuleType) {}

  // biome-ignore lint/suspicious/noExplicitAny: keys and values are heterogeneous AST entries
  public add(type: any, obj: any) {
    let items = this.subItems.get(type)
    if (items === undefined) {
      items = []
      this.subItems.set(type, items)
    }
    items.push(obj)
  }

  public getSingle(ruleType: RuleType) {
    return (this.subItems.get(ruleType) || [])[0]
  }

  public getItems(ruleType: RuleType) {
    return this.subItems.get(ruleType) || []
  }

  public getToken(tokenType: TokenType) {
    return (this.subItems.get(tokenType) || [])[0]
  }

  public getTokens(tokenType: TokenType): IToken<TokenType>[] {
    return this.subItems.get(tokenType) || []
  }
}
