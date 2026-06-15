import AstBuilder from './AstBuilder.js'
import Dialect from './Dialect.js'
import * as Errors from './Errors.js'
import GherkinClassicTokenMatcher from './GherkinClassicTokenMatcher.js'
import GherkinInMarkdownTokenMatcher from './GherkinInMarkdownTokenMatcher.js'
import generateMessages from './generateMessages.js'
import DIALECTS from './gherkin-languages.json' with { type: 'json' }
import IGherkinOptions from './IGherkinOptions.js'
import makeSourceEnvelope from './makeSourceEnvelope.js'
import Parser from './Parser.js'
import compile from './pickles/compile.js'
import TokenScanner from './TokenScanner.js'

const dialects = DIALECTS as Readonly<{ [key: string]: Dialect }>

export {
  AstBuilder,
  compile,
  Dialect,
  dialects,
  Errors,
  GherkinClassicTokenMatcher,
  GherkinInMarkdownTokenMatcher,
  generateMessages,
  IGherkinOptions,
  makeSourceEnvelope,
  Parser,
  TokenScanner,
}
