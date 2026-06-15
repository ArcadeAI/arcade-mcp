import * as messages from '@cucumber/messages'
import AstBuilder from './AstBuilder'
import GherkinClassicTokenMatcher from './GherkinClassicTokenMatcher'
import GherkinInMarkdownTokenMatcher from './GherkinInMarkdownTokenMatcher'
import type IGherkinOptions from './IGherkinOptions'
import type ITokenMatcher from './ITokenMatcher'
import makeSourceEnvelope from './makeSourceEnvelope'
import Parser, { type TokenType } from './Parser'
import compile from './pickles/compile'

export default function generateMessages(
  data: string,
  uri: string,
  mediaType: messages.SourceMediaType,
  options: IGherkinOptions
): readonly messages.Envelope[] {
  let tokenMatcher: ITokenMatcher<TokenType>
  switch (mediaType) {
    case messages.SourceMediaType.TEXT_X_CUCUMBER_GHERKIN_PLAIN:
      tokenMatcher = new GherkinClassicTokenMatcher(options.defaultDialect)
      break
    case messages.SourceMediaType.TEXT_X_CUCUMBER_GHERKIN_MARKDOWN:
      tokenMatcher = new GherkinInMarkdownTokenMatcher(options.defaultDialect)
      break
    default:
      throw new Error(`Unsupported media type: ${mediaType}`)
  }

  const result = []

  try {
    if (options.includeSource) {
      result.push(makeSourceEnvelope(data, uri))
    }

    if (!options.includeGherkinDocument && !options.includePickles) {
      return result
    }

    const parser = new Parser(new AstBuilder(options.newId), tokenMatcher)
    parser.stopAtFirstError = false

    const gherkinDocument = parser.parse(data)

    if (options.includeGherkinDocument) {
      result.push({
        gherkinDocument: { ...gherkinDocument, uri },
      })
    }

    if (options.includePickles) {
      const pickles = compile(gherkinDocument, uri, options.newId)
      for (const pickle of pickles) {
        result.push({
          pickle,
        })
      }
    }
  } catch (err) {
    const errors = err.errors || [err]
    for (const error of errors) {
      if (!error.location) {
        // It wasn't a parser error - throw it (this is unexpected)
        throw error
      }
      result.push({
        parseError: {
          source: {
            uri,
            location: {
              line: error.location.line,
              column: error.location.column,
            },
          },
          message: error.message,
        },
      })
    }
  }
  return result
}
