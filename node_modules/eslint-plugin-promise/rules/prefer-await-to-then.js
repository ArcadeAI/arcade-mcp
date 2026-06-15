/**
 * Rule: prefer-await-to-then
 * Discourage using then()/catch()/finally() and instead use async/await.
 */

'use strict'

const { getAncestors, getScope } = require('./lib/eslint-compat')
const getDocsUrl = require('./lib/get-docs-url')
const isMemberCallWithObjectName = require('./lib/is-member-call-with-object-name')

module.exports = {
  meta: {
    type: 'suggestion',
    docs: {
      description:
        'Prefer `await` to `then()`/`catch()`/`finally()` for reading Promise values.',
      url: getDocsUrl('prefer-await-to-then'),
    },
    schema: [
      {
        type: 'object',
        properties: {
          strict: {
            type: 'boolean',
          },
        },
      },
    ],
    messages: {
      preferAwaitToCallback: 'Prefer await to then()/catch()/finally().',
    },
  },
  create(context) {
    /** Returns true if node is inside yield or await expression. */
    function isInsideYieldOrAwait(node) {
      return getAncestors(context, node).some((parent) => {
        return (
          parent.type === 'AwaitExpression' || parent.type === 'YieldExpression'
        )
      })
    }

    /** Returns true if node is inside a constructor */
    function isInsideConstructor(node) {
      return getAncestors(context, node).some((parent) => {
        return (
          parent.type === 'MethodDefinition' && parent.kind === 'constructor'
        )
      })
    }

    /**
     * Returns true if node is created at the top-level scope.
     * Await statements are not allowed at the top level,
     * only within function declarations.
     */
    function isTopLevelScoped(node) {
      return getScope(context, node).block.type === 'Program'
    }

    const { strict } = context.options[0] || {}

    return {
      'CallExpression > MemberExpression.callee'(node) {
        if (
          isTopLevelScoped(node) ||
          (!strict && isInsideYieldOrAwait(node)) ||
          (!strict && isInsideConstructor(node)) ||
          isMemberCallWithObjectName('cy', node.parent)
        ) {
          return
        }

        // if you're a then/catch/finally expression then you're probably a promise
        if (
          node.property &&
          (node.property.name === 'then' ||
            node.property.name === 'catch' ||
            node.property.name === 'finally')
        ) {
          context.report({
            node: node.property,
            messageId: 'preferAwaitToCallback',
          })
        }
      },
    }
  },
}
