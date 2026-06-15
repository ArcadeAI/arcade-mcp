import type { ParsletFunction } from './Parslet.js'

export const uniqueSymbolParslet: ParsletFunction = (parser, _precedence, left) => {
  if (left !== null) {
    return null
  }

  if (
    parser.lexer.current.type !== 'Identifier' ||
    parser.lexer.current.text !== 'unique' ||
    parser.lexer.next.type !== 'Identifier' ||
    parser.lexer.next.text !== 'symbol'
  ) {
    return null
  }

  parser.consume('Identifier')
  parser.consume('Identifier')

  return {
    type: 'JsdocTypeUniqueSymbol'
  }
}
