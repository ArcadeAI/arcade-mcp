import { GherkinException } from './Errors'
import type IToken from './IToken'

export class UnexpectedTokenException extends GherkinException {
  public static create<TokenType>(token: IToken<TokenType>, expectedTokenTypes: string[]) {
    const message = `expected: ${expectedTokenTypes.join(', ')}, got '${token
      .getTokenValue()
      .trim()}'`

    const location = tokenLocation(token)

    return UnexpectedTokenException._create(message, location)
  }
}

export class UnexpectedEOFException extends GherkinException {
  public static create<TokenType>(token: IToken<TokenType>, expectedTokenTypes: string[]) {
    const message = `unexpected end of file, expected: ${expectedTokenTypes.join(', ')}`
    const location = tokenLocation(token)

    return UnexpectedEOFException._create(message, location)
  }
}

function tokenLocation<TokenType>(token: IToken<TokenType>) {
  return token.location?.line && token.line && token.line.indent !== undefined
    ? {
        line: token.location.line,
        column: token.line.indent + 1,
      }
    : token.location
}
