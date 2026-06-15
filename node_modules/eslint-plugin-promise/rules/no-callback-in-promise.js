/**
 * Rule: no-callback-in-promise
 * Avoid calling back inside of a promise
 */

'use strict'

const { getAncestors } = require('./lib/eslint-compat')
const getDocsUrl = require('./lib/get-docs-url')
const hasPromiseCallback = require('./lib/has-promise-callback')
const isInsidePromise = require('./lib/is-inside-promise')
const isCallback = require('./lib/is-callback')

const CB_BLACKLIST = ['callback', 'cb', 'next', 'done']
const TIMEOUT_WHITELIST = [
  'setImmediate',
  'setTimeout',
  'requestAnimationFrame',
  'nextTick',
]

const isInsideTimeout = (node) => {
  const isFunctionExpression =
    node.type === 'FunctionExpression' ||
    node.type === 'ArrowFunctionExpression'
  const parent = node.parent || {}
  const callee = parent.callee || {}
  const name = (callee.property && callee.property.name) || callee.name || ''
  const parentIsTimeout = TIMEOUT_WHITELIST.includes(name)
  const isInCB = isFunctionExpression && parentIsTimeout
  return isInCB
}

module.exports = {
  meta: {
    type: 'suggestion',
    docs: {
      description:
        'Disallow calling `cb()` inside of a `then()` (use [util.callbackify][] instead).',
      url: getDocsUrl('no-callback-in-promise'),
    },
    messages: {
      callback: 'Avoid calling back inside of a promise.',
    },
    schema: [
      {
        type: 'object',
        properties: {
          exceptions: {
            type: 'array',
            items: {
              type: 'string',
            },
          },
          timeoutsErr: {
            type: 'boolean',
          },
        },
        additionalProperties: false,
      },
    ],
  },
  create(context) {
    const { timeoutsErr = false } = context.options[0] || {}

    return {
      CallExpression(node) {
        const options = context.options[0] || {}
        const exceptions = options.exceptions || []
        if (!isCallback(node, exceptions)) {
          const name = node.arguments?.[0]?.name
          if (hasPromiseCallback(node)) {
            const callingName = node.callee.name || node.callee.property?.name
            if (
              !exceptions.includes(name) &&
              CB_BLACKLIST.includes(name) &&
              (timeoutsErr || !TIMEOUT_WHITELIST.includes(callingName))
            ) {
              context.report({
                node: node.arguments[0],
                messageId: 'callback',
              })
            }
            return
          }
          if (!timeoutsErr) {
            return
          }

          if (!name) {
            // Will be handled elsewhere
            return
          }
        }

        const ancestors = getAncestors(context, node)
        if (
          ancestors.some(isInsidePromise) &&
          (timeoutsErr || !ancestors.some(isInsideTimeout))
        ) {
          context.report({
            node,
            messageId: 'callback',
          })
        }
      },
    }
  },
}
