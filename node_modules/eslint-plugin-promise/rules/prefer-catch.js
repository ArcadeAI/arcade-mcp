/**
 * Rule: prefer-catch
 * Discourage using then(a, b) or then(null, b) and instead use catch().
 */

'use strict'

const getDocsUrl = require('./lib/get-docs-url')
const { getSourceCode } = require('./lib/eslint-compat')
const removeArgument = require('./fix/remove-argument')

module.exports = {
  meta: {
    type: 'suggestion',
    docs: {
      description:
        'Prefer `catch` to `then(a, b)`/`then(null, b)` for handling errors.',
      url: getDocsUrl('prefer-catch'),
    },
    fixable: 'code',
    schema: [],
    messages: {
      preferCatchToThen: 'Prefer `catch` to `then(a, b)`/`then(null, b)`.',
    },
  },
  create(context) {
    const sourceCode = getSourceCode(context)
    return {
      'CallExpression > MemberExpression.callee'(node) {
        if (
          node.property?.name === 'then' &&
          node.parent.arguments.length >= 2
        ) {
          context.report({
            node: node.property,
            messageId: 'preferCatchToThen',
            *fix(fixer) {
              const then = node.parent.arguments[0]
              if (
                (then.type === 'Literal' && then.value === null) ||
                (then.type === 'Identifier' && then.name === 'undefined')
              ) {
                yield removeArgument(fixer, then, sourceCode)
                yield fixer.replaceText(node.property, 'catch')
              } else {
                const catcher = node.parent.arguments[1]
                const catcherText = sourceCode.getText(catcher)
                yield removeArgument(fixer, catcher, sourceCode)
                yield fixer.insertTextBefore(
                  node.property,
                  `catch(${catcherText}).`,
                )
              }
            },
          })
        }
      },
    }
  },
}
