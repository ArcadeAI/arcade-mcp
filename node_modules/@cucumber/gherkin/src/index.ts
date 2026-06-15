import AstBuilder from './AstBuilder'
import Dialect from './Dialect'
import * as Errors from './Errors'
import GherkinClassicTokenMatcher from './GherkinClassicTokenMatcher'
import GherkinInMarkdownTokenMatcher from './GherkinInMarkdownTokenMatcher'
import generateMessages from './generateMessages'
import DIALECTS from './gherkin-languages.json'
import IGherkinOptions from './IGherkinOptions'
import makeSourceEnvelope from './makeSourceEnvelope'
import Parser from './Parser'
import compile from './pickles/compile'
import TokenScanner from './TokenScanner'

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
