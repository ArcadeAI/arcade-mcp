/**
 * Adapted from `eslint-plugin-unicorn`
 * @license MIT
 */

'use strict'
const { isCommaToken } = require('@eslint-community/eslint-utils')
const { getParentheses } = require('../lib/parentheses.js')

function removeArgument(fixer, node, sourceCode) {
  const callExpression = node.parent
  const index = callExpression.arguments.indexOf(node)
  const parentheses = getParentheses(node, sourceCode)
  const firstToken = parentheses[0] || node
  const lastToken = parentheses.at(-1) || node

  let [start] = firstToken.range
  let [, end] = lastToken.range

  if (index !== 0) {
    start = sourceCode.getTokenBefore(firstToken).range[0]
  }

  // If there are subsequent arguments, the trailing comma must be removed too
  /* istanbul ignore else */
  if (index < callExpression.arguments.length - 1) {
    let tokenAfter = sourceCode.getTokenAfter(lastToken)
    /* istanbul ignore else */
    if (isCommaToken(tokenAfter)) {
      // Advance to start of next token (after whitespace)
      tokenAfter = sourceCode.getTokenAfter(tokenAfter)
      end = tokenAfter.range[0]
    }
  }
  // If the removed argument is the only argument, the trailing comma must be removed too
  else if (callExpression.arguments.length === 1) {
    const tokenAfter = sourceCode.getTokenBefore(lastToken)
    if (isCommaToken(tokenAfter)) {
      end = tokenAfter[1]
    }
  }

  return fixer.replaceTextRange([start, end], '')
}

module.exports = removeArgument
