import type * as messages from '@cucumber/messages'
import type IToken from './IToken'

export interface IAstBuilder<AstNode, TokenType, RuleType> {
  stack: AstNode[]
  comments: messages.Comment[]
  newId: messages.IdGenerator.NewId

  reset(): void

  startRule(ruleType: RuleType): void

  endRule(): void

  build(token: IToken<TokenType>): void

  // biome-ignore lint/suspicious/noExplicitAny: result type varies per builder implementation
  getResult(): any

  // biome-ignore lint/suspicious/noExplicitAny: node representation varies per builder implementation
  currentNode(): any

  getLocation(token: IToken<TokenType>, column?: number): messages.Location

  getTags(node: AstNode): readonly messages.Tag[]

  getCells(tableRowToken: IToken<TokenType>): readonly messages.TableCell[]

  // biome-ignore lint/suspicious/noExplicitAny: description type varies per builder implementation
  getDescription(node: AstNode): any

  // biome-ignore lint/suspicious/noExplicitAny: step representation varies per builder implementation
  getSteps(node: AstNode): any[]

  getTableRows(node: AstNode): readonly messages.TableRow[] | undefined

  ensureCellCount(rows: readonly messages.TableRow[]): void

  // biome-ignore lint/suspicious/noExplicitAny: transformed node varies per rule type
  transformNode(node: AstNode): any
}
